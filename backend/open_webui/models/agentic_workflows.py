import re
import time
from typing import Literal, Optional
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.agents import AgentFlowConfig
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, BigInteger, Boolean, Column, Text, select
from sqlalchemy.ext.asyncio import AsyncSession


class AgenticWorkflowConfiguration(Base):
    __tablename__ = 'agentic_workflow_configuration'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    tool_name = Column(Text, nullable=False, unique=True, index=True)
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False, index=True)


class AgenticWorkflowNode(BaseModel):
    agent_id: str = Field(min_length=1, max_length=160)
    model_id: str = Field(min_length=1, max_length=300)
    instruction: str = Field(default='', max_length=4000)


class AgenticWorkflowConfig(BaseModel):
    engine: Literal['langgraph'] = 'langgraph'
    trigger: Literal['openclaw-tool'] = 'openclaw-tool'
    task_queue: str = 'pengurusan-ai-agents'
    timeout_seconds: int = Field(default=3600, ge=30, le=86400)
    max_retries: int = Field(default=3, ge=0, le=20)
    nodes: list[AgenticWorkflowNode] = Field(default_factory=list)
    visible_in_chat: bool = True
    # Kept for reading workflows saved by the earlier Voice Intelligence UI.
    executor_agent_id: str = ''
    allowed_agent_ids: list[str] = Field(default_factory=list)
    flow: Optional[AgentFlowConfig] = None

    @field_validator('allowed_agent_ids')
    @classmethod
    def unique_agents(cls, values: list[str]):
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class AgenticWorkflowForm(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    tool_name: str = Field(min_length=3, max_length=80)
    config: AgenticWorkflowConfig = Field(default_factory=AgenticWorkflowConfig)
    is_active: bool = True

    @field_validator('tool_name')
    @classmethod
    def valid_tool_name(cls, value: str):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z][a-z0-9_]*', value):
            raise ValueError('Tool name must use lowercase letters, numbers, and underscores')
        return value


class AgenticWorkflowModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    tool_name: str
    config: AgenticWorkflowConfig
    is_active: bool
    created_at: int
    updated_at: int


class AgenticWorkflowConfigurationsTable:
    async def list(self, db: Optional[AsyncSession] = None) -> list[AgenticWorkflowModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AgenticWorkflowConfiguration).order_by(AgenticWorkflowConfiguration.updated_at.desc())
            )
            return [AgenticWorkflowModel.model_validate(row) for row in result.scalars().all()]

    async def get(self, workflow_id: str, db: Optional[AsyncSession] = None) -> Optional[AgenticWorkflowModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgenticWorkflowConfiguration, workflow_id)
            return AgenticWorkflowModel.model_validate(row) if row else None

    async def get_by_tool_name(
        self, tool_name: str, db: Optional[AsyncSession] = None
    ) -> Optional[AgenticWorkflowModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AgenticWorkflowConfiguration).where(AgenticWorkflowConfiguration.tool_name == tool_name)
            )
            row = result.scalar_one_or_none()
            return AgenticWorkflowModel.model_validate(row) if row else None

    async def insert(
        self, user_id: str, form: AgenticWorkflowForm, db: Optional[AsyncSession] = None
    ) -> AgenticWorkflowModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            row = AgenticWorkflowConfiguration(
                id=str(uuid4()),
                user_id=user_id,
                name=form.name.strip(),
                description=form.description,
                tool_name=form.tool_name,
                config=form.config.model_dump(),
                is_active=form.is_active,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return AgenticWorkflowModel.model_validate(row)

    async def update(
        self, workflow_id: str, form: AgenticWorkflowForm, db: Optional[AsyncSession] = None
    ) -> Optional[AgenticWorkflowModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgenticWorkflowConfiguration, workflow_id)
            if not row:
                return None
            row.name = form.name.strip()
            row.description = form.description
            row.tool_name = form.tool_name
            row.config = form.config.model_dump()
            row.is_active = form.is_active
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgenticWorkflowModel.model_validate(row)

    async def delete(self, workflow_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            row = await db.get(AgenticWorkflowConfiguration, workflow_id)
            if not row:
                return False
            await db.delete(row)
            await db.commit()
            return True


AgenticWorkflowConfigurations = AgenticWorkflowConfigurationsTable()
