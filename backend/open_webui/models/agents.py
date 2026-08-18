import hmac
import time
from typing import Literal, Optional
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import JSON, BigInteger, Boolean, Column, Text, select
from sqlalchemy.ext.asyncio import AsyncSession


class AgentConfiguration(Base):
    __tablename__ = 'agent_configuration'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=False)
    code_path = Column(Text, nullable=True)
    code_filename = Column(Text, nullable=True)
    code_sha256 = Column(Text, nullable=True)
    code_validation = Column(JSON, nullable=True)
    api_key_hash = Column(Text, nullable=True)
    api_key_prefix = Column(Text, nullable=True)
    api_key_created_at = Column(BigInteger, nullable=True)
    api_key_last_used_at = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False, index=True)

    @property
    def api_key_configured(self) -> bool:
        return bool(self.api_key_hash)


class AgentModelConfig(BaseModel):
    kind: Literal['llm', 'whisper'] = 'llm'
    provider: Literal['platform', 'ollama', 'openai', 'anthropic', 'google', 'local'] = 'platform'
    model_id: str = ''
    stt_model: str = 'base'
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=128, le=131072)


class AgentOrchestrationConfig(BaseModel):
    engine: Literal['local', 'temporal'] = 'temporal'
    workflow_name: str = 'pengurusan_ai.agent.run'
    task_queue: str = 'pengurusan-ai-agents'
    media_task_queue: str = 'MEDIA_TASK_QUEUE'
    asr_task_queue: str = 'ASR_TASK_QUEUE'
    timeout_seconds: int = Field(default=900, ge=30, le=86400)
    max_retries: int = Field(default=3, ge=0, le=20)


class AgentStorageConfig(BaseModel):
    provider: Literal['inherit', 'minio', 'local'] = 'inherit'
    bucket: Optional[str] = None
    prefix: str = 'agents'
    save_originals: bool = True
    save_outputs: bool = True
    retention_days: int = Field(default=30, ge=0, le=3650)


class AgentChunkingConfig(BaseModel):
    enabled: bool = True
    strategy: Literal['recursive', 'token', 'sentence', 'semantic'] = 'recursive'
    chunk_size: int = Field(default=1000, ge=100, le=20000)
    chunk_overlap: int = Field(default=150, ge=0, le=5000)
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'

    @model_validator(mode='after')
    def validate_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError('Chunk overlap must be smaller than chunk size')
        return self


class AgentRuntimeConfig(BaseModel):
    mode: Literal['builtin', 'python'] = 'builtin'
    entrypoint: str = 'run'
    allow_network: bool = False
    memory_mb: int = Field(default=512, ge=128, le=16384)


class AgentOpenClawConfig(BaseModel):
    agent_id: str = ''
    workspace: str = ''
    thinking: Literal['off', 'minimal', 'low', 'medium', 'high'] = 'medium'
    sandbox: bool = True


class AgentFlowStageConfig(BaseModel):
    enabled: bool = True
    component: str
    agent_id: str = ''
    provider: str = 'local'
    model_id: str = ''
    prompt: str = ''
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_options(self):
        if self.component == 'transcript-chunking':
            chunk_size = int(self.options.get('chunk_size', 1000))
            chunk_overlap = int(self.options.get('chunk_overlap', 150))
            if chunk_size < 100 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
                raise ValueError('Chunk size must be at least 100 and overlap must be smaller than chunk size')
        return self


def default_voice_flow_stages() -> list[AgentFlowStageConfig]:
    return [
        AgentFlowStageConfig(component='faster-whisper', model_id='small'),
        AgentFlowStageConfig(
            component='pyannote-diarization',
            model_id='pyannote/speaker-diarization-community-1',
        ),
        AgentFlowStageConfig(
            component='transcript-chunking',
            model_id='recursive',
            options={'chunk_size': 1000, 'chunk_overlap': 150},
        ),
        AgentFlowStageConfig(
            component='openclaw-topic',
            provider='openclaw',
            prompt='Ekstrak topik utama dan bukti ringkas daripada transkrip.',
        ),
        AgentFlowStageConfig(
            component='openclaw-summary',
            provider='openclaw',
            prompt='Ringkaskan transkrip dengan keputusan, isu, tindakan, pegawai dan tarikh akhir.',
        ),
        AgentFlowStageConfig(
            component='openclaw-thematic',
            provider='openclaw',
            prompt='Kenal pasti tema utama, subtema dan bukti ringkas daripada transkrip.',
        ),
    ]


class AgentFlowConfig(BaseModel):
    enabled: bool = False
    engine: Literal['langgraph'] = 'langgraph'
    template: Literal['voice-intelligence-v1'] = 'voice-intelligence-v1'
    stages: list[AgentFlowStageConfig] = Field(default_factory=default_voice_flow_stages)

    @field_validator('stages')
    @classmethod
    def validate_stages(cls, stages: list[AgentFlowStageConfig]):
        allowed = {
            'faster-whisper',
            'pyannote-diarization',
            'speechbrain-diarization',
            'transcript-chunking',
            'openclaw-topic',
            'openclaw-summary',
            'openclaw-thematic',
        }
        components = [stage.component for stage in stages]
        if any(component not in allowed for component in components):
            raise ValueError('Unsupported voice flow component')
        if len(components) != len(set(components)):
            raise ValueError('Voice flow components must be unique')
        return stages

    @model_validator(mode='after')
    def validate_enabled_flow(self):
        enabled = [stage.component for stage in self.stages if stage.enabled]
        if self.enabled and 'faster-whisper' not in enabled:
            raise ValueError('An enabled voice flow requires faster-whisper')
        if self.enabled and enabled and enabled[0] != 'faster-whisper':
            raise ValueError('An enabled voice flow must begin with faster-whisper')
        diarization = {'pyannote-diarization', 'speechbrain-diarization'}
        if len(diarization.intersection(enabled)) > 1:
            raise ValueError('Enable only one diarization component')
        return self


class AgentConfig(BaseModel):
    framework: Literal['openclaw'] = 'openclaw'
    template: str = 'custom'
    instructions: str = ''
    capabilities: list[str] = Field(default_factory=lambda: ['chat'])
    tools: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    model: AgentModelConfig = Field(default_factory=AgentModelConfig)
    orchestration: AgentOrchestrationConfig = Field(default_factory=AgentOrchestrationConfig)
    storage: AgentStorageConfig = Field(default_factory=AgentStorageConfig)
    chunking: AgentChunkingConfig = Field(default_factory=AgentChunkingConfig)
    runtime: AgentRuntimeConfig = Field(default_factory=AgentRuntimeConfig)
    components: list[str] = Field(default_factory=list)
    openclaw: AgentOpenClawConfig = Field(default_factory=AgentOpenClawConfig)

    @field_validator('capabilities')
    @classmethod
    def unique_capabilities(cls, value: list[str]):
        return list(dict.fromkeys(value))


class AgentForm(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    config: AgentConfig = Field(default_factory=AgentConfig)
    is_active: bool = True


class AgentSettingsForm(BaseModel):
    model_id: str = Field(min_length=1, max_length=300)
    model_type: Literal['llm', 'whisper'] = 'llm'
    stt_model: Optional[str] = Field(default=None, max_length=120)
    provider: Optional[str] = Field(default=None, max_length=80)
    is_active: bool = True


class AgentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    config: AgentConfig
    code_path: Optional[str] = None
    code_filename: Optional[str] = None
    code_sha256: Optional[str] = None
    code_validation: Optional[dict] = None
    api_key_configured: bool = False
    api_key_prefix: Optional[str] = None
    api_key_created_at: Optional[int] = None
    api_key_last_used_at: Optional[int] = None
    is_active: bool
    created_at: int
    updated_at: int


class AgentConfigurationsTable:
    async def list(self, db: Optional[AsyncSession] = None) -> list[AgentModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(AgentConfiguration).order_by(AgentConfiguration.updated_at.desc()))
            return [AgentModel.model_validate(row) for row in result.scalars().all()]

    async def get(self, agent_id: str, db: Optional[AsyncSession] = None) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            return AgentModel.model_validate(row) if row else None

    async def get_by_openclaw_id(
        self, openclaw_agent_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(AgentConfiguration))
            for row in result.scalars().all():
                config = row.config or {}
                if config.get('openclaw', {}).get('agent_id') == openclaw_agent_id:
                    return AgentModel.model_validate(row)
            return None

    async def insert(self, user_id: str, form: AgentForm, db: Optional[AsyncSession] = None) -> AgentModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            row = AgentConfiguration(
                id=str(uuid4()),
                user_id=user_id,
                name=form.name.strip(),
                description=form.description,
                config=form.config.model_dump(),
                is_active=form.is_active,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def update(self, agent_id: str, form: AgentForm, db: Optional[AsyncSession] = None) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            row.name = form.name.strip()
            row.description = form.description
            row.config = form.config.model_dump()
            row.is_active = form.is_active
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def update_settings(
        self,
        agent_id: str,
        model_id: str,
        is_active: bool,
        provider: str = 'platform',
        model_type: str = 'llm',
        stt_model: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            config = dict(row.config or {})
            config['model'] = {
                **config.get('model', {}),
                'provider': provider,
                'model_id': model_id,
                'kind': model_type,
                **({'stt_model': stt_model} if stt_model else {}),
            }
            config.pop('flow', None)
            row.config = config
            row.is_active = is_active
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def set_api_key(
        self, agent_id: str, key_hash: str, key_prefix: str, db: Optional[AsyncSession] = None
    ) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            now = int(time.time())
            row.api_key_hash = key_hash
            row.api_key_prefix = key_prefix
            row.api_key_created_at = now
            row.api_key_last_used_at = None
            row.updated_at = now
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def revoke_api_key(self, agent_id: str, db: Optional[AsyncSession] = None) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            row.api_key_hash = None
            row.api_key_prefix = None
            row.api_key_created_at = None
            row.api_key_last_used_at = None
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def authenticate_api_key(
        self, agent_id: str, key_hash: str, db: Optional[AsyncSession] = None
    ) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row or not row.api_key_hash or not hmac.compare_digest(row.api_key_hash, key_hash):
                return None
            row.api_key_last_used_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row)

    async def set_code(self, agent_id: str, path: str, filename: str, sha256: str, validation: dict, db=None):
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            old_path = row.code_path
            row.code_path = path
            row.code_filename = filename
            row.code_sha256 = sha256
            row.code_validation = validation
            config = dict(row.config or {})
            config['runtime'] = {**config.get('runtime', {}), 'mode': 'python'}
            row.config = config
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return AgentModel.model_validate(row), old_path

    async def delete(self, agent_id: str, db=None) -> Optional[AgentModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(AgentConfiguration, agent_id)
            if not row:
                return None
            model = AgentModel.model_validate(row)
            await db.delete(row)
            await db.commit()
            return model


AgentConfigurations = AgentConfigurationsTable()
