import hashlib
import hmac
import os
from datetime import timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from open_webui.internal.db import get_async_session
from open_webui.models.agentic_workflows import (
    AgenticWorkflowConfigurations,
    AgenticWorkflowForm,
    AgenticWorkflowModel,
)
from open_webui.models.agents import AgentConfigurations
from open_webui.utils.auth import get_admin_user
from pengurusan_temporal_workflows import AGENT_CHAIN_WORKFLOW
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class WorkflowRunForm(BaseModel):
    message: str = Field(min_length=1, max_length=200000)
    job_id: Optional[str] = Field(default=None, max_length=160)


class WorkflowToolRunForm(WorkflowRunForm):
    caller_agent_id: str = Field(min_length=1, max_length=160)


def _validate_mcp_token(authorization: Optional[str]):
    expected = os.getenv('AGENTIC_MCP_TOKEN', '')
    scheme, _, supplied = (authorization or '').partition(' ')
    if (
        not expected
        or scheme.lower() != 'bearer'
        or not hmac.compare_digest(
            hashlib.sha256(supplied.encode()).digest(), hashlib.sha256(expected.encode()).digest()
        )
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid MCP bridge token')


async def _validate_nodes(form: AgenticWorkflowForm, db: AsyncSession):
    if not form.config.nodes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Add at least one agent')
    for node in form.config.nodes:
        agent = await AgentConfigurations.get(node.agent_id, db=db)
        if not agent or not agent.config.openclaw.agent_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='A workflow agent does not exist in OpenClaw'
            )
        if not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f'Activate agent {agent.name} before saving'
            )


async def _start_workflow(item: AgenticWorkflowModel, message: str, job_id: Optional[str]):
    if not item.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Agentic workflow is inactive')
    if not item.config.nodes:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Add at least one agent to the workflow')
    stage_agents = [await AgentConfigurations.get(node.agent_id) for node in item.config.nodes]
    if any(not agent or not agent.is_active or not agent.config.openclaw.agent_id for agent in stage_agents):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='A node agent is missing, inactive, or not linked to OpenClaw'
        )
    nodes = [
        {
            **node.model_dump(),
            'agent_name': agent.name,
            'openclaw_agent_id': agent.config.openclaw.agent_id,
        }
        for node, agent in zip(item.config.nodes, stage_agents)
    ]
    if os.getenv('TEMPORAL_ENABLED', 'false').lower() != 'true':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Temporal is not enabled')

    from temporalio.client import Client

    client = await Client.connect(
        os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'),
        namespace=os.getenv('TEMPORAL_NAMESPACE', 'default'),
        tls=os.getenv('TEMPORAL_TLS', 'false').lower() == 'true',
        api_key=os.getenv('TEMPORAL_API_KEY', '') or None,
    )
    workflow_id = f'agentic-{item.id}-{uuid4().hex}'
    handle = await client.start_workflow(
        AGENT_CHAIN_WORKFLOW,
        {
            'agentic_workflow_id': item.id,
            'message': message,
            'nodes': nodes,
            'session_key': job_id or workflow_id,
            'timeout_seconds': item.config.timeout_seconds,
            'max_retries': item.config.max_retries,
        },
        id=workflow_id,
        task_queue=item.config.task_queue,
        execution_timeout=timedelta(seconds=item.config.timeout_seconds),
    )
    return {'started': True, 'workflow_id': handle.id, 'run_id': handle.result_run_id}


@router.get('/', response_model=list[AgenticWorkflowModel])
async def list_workflows(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    return await AgenticWorkflowConfigurations.list(db=db)


@router.get('/runs/{workflow_id}/status')
async def get_run_status(workflow_id: str, user=Depends(get_admin_user)):
    if os.getenv('TEMPORAL_ENABLED', 'false').lower() != 'true':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Temporal is not enabled')
    try:
        from temporalio.client import Client

        client = await Client.connect(
            os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'),
            namespace=os.getenv('TEMPORAL_NAMESPACE', 'default'),
            tls=os.getenv('TEMPORAL_TLS', 'false').lower() == 'true',
            api_key=os.getenv('TEMPORAL_API_KEY', '') or None,
        )
        return await client.get_workflow_handle(workflow_id).query('status')
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to query workflow: {exc}')


@router.post('/create', response_model=AgenticWorkflowModel)
async def create_workflow(
    form: AgenticWorkflowForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _validate_nodes(form, db)
    try:
        return await AgenticWorkflowConfigurations.insert(user.id, form, db=db)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool name is already in use')


@router.post('/{workflow_id}/update', response_model=AgenticWorkflowModel)
async def update_workflow(
    workflow_id: str,
    form: AgenticWorkflowForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _validate_nodes(form, db)
    try:
        updated = await AgenticWorkflowConfigurations.update(workflow_id, form, db=db)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Tool name is already in use')
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agentic workflow not found')
    return updated


@router.delete('/{workflow_id}')
async def delete_workflow(
    workflow_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not await AgenticWorkflowConfigurations.delete(workflow_id, db=db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agentic workflow not found')
    return {'success': True}


@router.post('/{workflow_id}/run')
async def run_workflow(
    workflow_id: str,
    form: WorkflowRunForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    item = await AgenticWorkflowConfigurations.get(workflow_id, db=db)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agentic workflow not found')
    try:
        return await _start_workflow(item, form.message, form.job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to start workflow: {exc}')


@router.post('/tools/{tool_name}/invoke')
async def invoke_workflow_tool(
    tool_name: str,
    form: WorkflowToolRunForm,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_async_session),
):
    _validate_mcp_token(authorization)
    item = await AgenticWorkflowConfigurations.get_by_tool_name(tool_name, db=db)
    if not item or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Active workflow tool not found')
    try:
        return await _start_workflow(item, form.message, form.job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to start workflow: {exc}')


@router.get('/tools/catalog/{caller_agent_id}')
async def workflow_tool_catalog(
    caller_agent_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_async_session),
):
    _validate_mcp_token(authorization)
    items = await AgenticWorkflowConfigurations.list(db=db)
    return [
        {
            'name': item.tool_name,
            'title': item.name,
            'description': item.description or f'Run the {item.name} agentic workflow',
        }
        for item in items
        if item.is_active and item.config.nodes
    ]
