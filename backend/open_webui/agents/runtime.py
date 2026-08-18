"""Durable execution helpers for Pengurusan AI OpenClaw agents."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import timedelta
from uuid import uuid4

from open_webui.models.agentic_workflows import AgenticWorkflowModel
from open_webui.models.agents import AgentConfigurations, AgentModel
from pengurusan_temporal_workflows import AGENT_CHAIN_WORKFLOW, OPENCLAW_CHAT_WORKFLOW


def temporal_enabled() -> bool:
    return os.getenv('TEMPORAL_ENABLED', 'false').lower() == 'true'


async def invoke_openclaw_via_temporal(
    agent: AgentModel,
    message: str,
    *,
    session_key: str | None = None,
    user_id: str | None = None,
    chat_id: str | None = None,
) -> dict:
    """Run one OpenClaw turn through Temporal and wait for its durable result."""
    if not temporal_enabled():
        raise RuntimeError('Temporal is not enabled')
    if agent.config.orchestration.engine != 'temporal':
        raise RuntimeError('This agent is not configured to use Temporal')
    if not agent.config.openclaw.agent_id:
        raise RuntimeError('Agent is not linked to OpenClaw')

    from temporalio.client import Client

    timeout = agent.config.orchestration.timeout_seconds
    client = await Client.connect(
        os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'),
        namespace=os.getenv('TEMPORAL_NAMESPACE', 'default'),
        tls=os.getenv('TEMPORAL_TLS', 'false').lower() == 'true',
        api_key=os.getenv('TEMPORAL_API_KEY', '') or None,
    )
    handle = await client.start_workflow(
        OPENCLAW_CHAT_WORKFLOW,
        {
            'agent_id': agent.id,
            'message': message,
            'session_key': session_key,
            'user_id': user_id,
            'chat_id': chat_id,
            'timeout_seconds': timeout,
            'max_retries': agent.config.orchestration.max_retries,
        },
        id=f'openclaw-chat-{agent.id}-{uuid4().hex}',
        task_queue=os.getenv('TEMPORAL_TASK_QUEUE', 'pengurusan-ai-agents'),
        execution_timeout=timedelta(seconds=timeout),
    )
    try:
        result = await handle.result()
    except asyncio.CancelledError:
        try:
            await asyncio.shield(handle.cancel())
        except BaseException:
            pass
        raise
    except Exception as exc:
        root = exc
        seen: set[int] = set()
        while getattr(root, '__cause__', None) is not None and id(root) not in seen:
            seen.add(id(root))
            root = root.__cause__
        detail = str(root).strip() or type(root).__name__
        raise RuntimeError(f'Temporal agent activity failed: {detail}') from exc
    if isinstance(result, dict):
        return {
            **result,
            'temporal': {
                'workflow_id': handle.id,
                'run_id': handle.result_run_id,
                'task_queue': os.getenv('TEMPORAL_TASK_QUEUE', 'pengurusan-ai-agents'),
            },
        }
    return {
        'result': result,
        'temporal': {
            'workflow_id': handle.id,
            'run_id': handle.result_run_id,
            'task_queue': os.getenv('TEMPORAL_TASK_QUEUE', 'pengurusan-ai-agents'),
        },
    }


async def invoke_agentic_workflow_via_temporal(
    item: AgenticWorkflowModel,
    message: str,
    *,
    session_key: str,
    user_id: str | None = None,
    chat_id: str | None = None,
    progress_callback: Callable[[dict], Awaitable[None]] | None = None,
) -> dict:
    """Run the configured OpenClaw agent chain and wait for its final node."""
    if not temporal_enabled():
        raise RuntimeError('Temporal is not enabled')
    if not item.is_active or not item.config.nodes:
        raise RuntimeError('Agentic workflow is inactive or has no agents')

    from temporalio.client import Client

    client = await Client.connect(
        os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'),
        namespace=os.getenv('TEMPORAL_NAMESPACE', 'default'),
        tls=os.getenv('TEMPORAL_TLS', 'false').lower() == 'true',
        api_key=os.getenv('TEMPORAL_API_KEY', '') or None,
    )
    nodes = []
    for node in item.config.nodes:
        node_agent = await AgentConfigurations.get(node.agent_id)
        nodes.append(
            {
                **node.model_dump(),
                'agent_name': node_agent.name if node_agent else node.agent_id,
                'openclaw_agent_id': (node_agent.config.openclaw.agent_id if node_agent else node.agent_id),
            }
        )

    handle = await client.start_workflow(
        AGENT_CHAIN_WORKFLOW,
        {
            'agentic_workflow_id': item.id,
            'message': message,
            'nodes': nodes,
            'session_key': session_key,
            'user_id': user_id,
            'chat_id': chat_id,
            'timeout_seconds': item.config.timeout_seconds,
            'max_retries': item.config.max_retries,
        },
        id=f'agentic-chain-{item.id}-{uuid4().hex}',
        task_queue=item.config.task_queue,
        execution_timeout=timedelta(seconds=item.config.timeout_seconds),
    )
    result_task = asyncio.create_task(handle.result())
    seen_outputs = 0
    announced_steps: set[int] = set()
    total_steps = len(item.config.nodes)

    async def announce_running(
        step: int,
        agent_id: str | None,
        agent_name: str | None,
        instruction: str | None,
    ) -> None:
        if not progress_callback or step in announced_steps or step > total_steps:
            return
        announced_steps.add(step)
        await progress_callback(
            {
                'state': 'running',
                'agent_id': agent_id,
                'agent_name': agent_name,
                'instruction': instruction,
                'step': step,
                'total': total_steps,
            }
        )

    async def announce_completed(output: dict) -> None:
        nonlocal seen_outputs
        step = seen_outputs + 1
        # A fast activity can finish between Temporal status polls. Synthesize
        # its start event so the UI still receives a strictly ordered queue.
        await announce_running(
            step,
            output.get('agent_id'),
            output.get('agent_name') or output.get('openclaw_agent_id'),
            output.get('instruction'),
        )
        if progress_callback:
            await progress_callback(
                {
                    'state': 'completed',
                    'step': step,
                    'total': total_steps,
                    'output': output,
                }
            )
        seen_outputs += 1

    try:
        while not result_task.done():
            try:
                workflow_status = await handle.query('status')
                next_step = workflow_status.get('current_step')
                next_agent_name = workflow_status.get('current_agent_name')
                instruction = workflow_status.get('current_instruction')
                outputs = workflow_status.get('outputs') or []
                # Report completed work first. Only then announce the next
                # active node, matching the actual sequential workflow queue.
                for output in outputs[seen_outputs:]:
                    await announce_completed(output)
                if next_step:
                    await announce_running(
                        len(outputs) + 1,
                        next_step,
                        next_agent_name,
                        instruction,
                    )
            except Exception:
                # Queries may briefly fail while Temporal admits the workflow.
                # The durable workflow result remains authoritative.
                pass
            await asyncio.wait({result_task}, timeout=0.5)

        result = await result_task
        if progress_callback:
            for output in (result.get('outputs') or [])[seen_outputs:]:
                await announce_completed(output)
            await progress_callback(
                {
                    'state': 'workflow_completed',
                    'total': total_steps,
                }
            )
    except asyncio.CancelledError:
        try:
            await asyncio.shield(handle.cancel())
        except BaseException:
            pass
        if not result_task.done():
            result_task.cancel()
        if progress_callback:
            try:
                await progress_callback(
                    {
                        'state': 'workflow_cancelled',
                        'total': len(item.config.nodes),
                    }
                )
            except BaseException:
                pass
        raise
    except Exception as exc:
        if not result_task.done():
            result_task.cancel()
        root = exc
        seen: set[int] = set()
        while getattr(root, '__cause__', None) is not None and id(root) not in seen:
            seen.add(id(root))
            root = root.__cause__
        detail = str(root).strip() or type(root).__name__
        raise RuntimeError(f'Temporal agentic workflow failed: {detail}') from exc
    return {
        **result,
        'temporal': {
            'workflow_id': handle.id,
            'run_id': handle.result_run_id,
            'task_queue': item.config.task_queue,
        },
    }


def openclaw_text(result: dict) -> str:
    """Extract user-visible text from OpenClaw's JSON result."""
    payloads = result.get('payloads') if isinstance(result, dict) else None
    if isinstance(payloads, list):
        texts = [item.get('text', '').strip() for item in payloads if isinstance(item, dict)]
        content = '\n\n'.join(text for text in texts if text)
        if content:
            return content

    if isinstance(result, dict):
        for key in ('text', 'content', 'message', 'output', 'response', 'result'):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = openclaw_text(value)
                if nested:
                    return nested

    raise RuntimeError('OpenClaw completed without a text response')
