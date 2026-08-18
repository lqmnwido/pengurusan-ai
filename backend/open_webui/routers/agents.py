import ast
import asyncio
import hashlib
import importlib.util
import io
import os
import re
import secrets
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from open_webui.agents import openclaw
from open_webui.agents.runtime import invoke_openclaw_via_temporal
from open_webui.config import S3_BUCKET_NAME, S3_ENDPOINT_URL, STORAGE_PROVIDER, WHISPER_MODEL_DIR
from open_webui.internal.db import get_async_session
from open_webui.models.agents import AgentConfigurations, AgentForm, AgentModel, AgentSettingsForm
from open_webui.routers.audio import set_faster_whisper_model
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

MAX_AGENT_CODE_BYTES = 512 * 1024
DANGEROUS_IMPORTS = {'ctypes', 'multiprocessing', 'pickle', 'resource', 'shutil', 'socket', 'subprocess'}
DANGEROUS_CALLS = {'__import__', 'compile', 'eval', 'exec', 'open'}
WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3', 'distil-large-v3']
ASR_WORKFLOW_NAME = os.getenv('TEMPORAL_ASR_WORKFLOW', 'AsrWorkflow::start')

AI_COMPONENTS = [
    {
        'id': 'whisper-stt',
        'name': 'Whisper Speech-to-Text',
        'category': 'audio',
        'description': 'Transkripsi audio berbilang bahasa menggunakan faster-whisper.',
        'capability': 'voice_to_text',
        'package': 'faster-whisper',
        'variants': WHISPER_MODELS,
        'default_variant': 'small',
        'size_hint': '75 MB – 3 GB',
    },
    {
        'id': 'pyannote-diarization',
        'name': 'Pyannote Speaker Diarization',
        'category': 'audio',
        'description': 'Kenal pasti siapa bercakap dan segmen masa setiap penutur.',
        'capability': 'diarization',
        'package': 'pyannote.audio',
        'package_spec': 'pyannote.audio==4.0.7',
        'variants': ['pyannote/speaker-diarization-community-1'],
        'default_variant': 'pyannote/speaker-diarization-community-1',
        'requires_token': True,
        'requires_terms': True,
        'size_hint': '≈ 1–2 GB',
    },
    {
        'id': 'speechbrain-diarization',
        'name': 'SpeechBrain + Silero Diarization',
        'category': 'audio',
        'description': 'Diarisasi tersuai menggunakan ECAPA speaker embeddings, Silero VAD dan padanan penutur merentas chunk.',
        'capability': 'diarization',
        'package': 'speechbrain',
        'package_specs': ['speechbrain', 'silero-vad'],
        'variants': ['speechbrain/spkrec-ecapa-voxceleb'],
        'default_variant': 'speechbrain/spkrec-ecapa-voxceleb',
        'size_hint': '≈ 500 MB',
        'reference_profile': 'temporal-asr',
    },
    {
        'id': 'blip-vision',
        'name': 'BLIP Image Recognition',
        'category': 'vision',
        'description': 'Fahami dan hasilkan penerangan kandungan imej secara lokal.',
        'capability': 'image_recognition',
        'package': 'transformers',
        'variants': ['Salesforce/blip-image-captioning-base'],
        'default_variant': 'Salesforce/blip-image-captioning-base',
        'size_hint': '≈ 1 GB',
    },
    {
        'id': 'rapidocr',
        'name': 'RapidOCR',
        'category': 'vision',
        'description': 'Ekstrak teks daripada imej dan dokumen imbasan.',
        'capability': 'ocr',
        'package': 'rapidocr_onnxruntime',
        'variants': ['default'],
        'default_variant': 'default',
        'size_hint': '≈ 100 MB',
    },
    {
        'id': 'custom-python-component',
        'name': 'Komponen Python Tersuai',
        'category': 'custom',
        'description': 'Bina diarization atau pemproses khusus melalui fail .py dan Temporal worker.',
        'capability': 'custom_code',
        'package': None,
        'variants': [],
        'default_variant': None,
        'custom': True,
        'size_hint': 'Bergantung pada kod',
    },
]


AGENT_TEMPLATES = [
    {
        'id': 'voice-transcription',
        'name': 'Analisis Mesyuarat ASR',
        'description': 'ASR, diarization, ringkasan dan analisis tematik melalui Temporal, dengan semua artifak di MinIO.',
        'icon': 'microphone',
        'config': {
            'template': 'voice-transcription',
            'instructions': 'Proses rakaman mesyuarat dengan tepat. Kenal pasti penutur, kekalkan nama dan istilah asal, hasilkan ringkasan serta tema utama dengan bukti daripada transkrip.',
            'capabilities': [
                'voice_to_text',
                'diarization',
                'summary',
                'thematic_analysis',
                'file_ingestion',
                'chunking',
                'file_output',
            ],
            'model': {
                'provider': 'local',
                'model_id': '',
                'stt_model': 'small',
                'temperature': 0.0,
                'max_tokens': 4096,
            },
            'orchestration': {
                'engine': 'temporal',
                'workflow_name': ASR_WORKFLOW_NAME,
                'task_queue': os.getenv('TEMPORAL_ASR_WORKFLOW_TASK_QUEUE', 'ASR_WORKFLOW_QUEUE'),
                'media_task_queue': os.getenv('TEMPORAL_MEDIA_TASK_QUEUE', 'MEDIA_TASK_QUEUE'),
                'asr_task_queue': os.getenv('TEMPORAL_ASR_TASK_QUEUE', 'ASR_TASK_QUEUE'),
            },
            'components': ['whisper-stt', 'speechbrain-diarization'],
        },
    },
    {
        'id': 'document-intelligence',
        'name': 'Dokumen Pintar',
        'description': 'Ekstrak, chunk, indeks dan jawab soalan berdasarkan dokumen yang dimuat naik.',
        'icon': 'document',
        'config': {
            'template': 'document-intelligence',
            'instructions': 'Jawab berdasarkan dokumen. Nyatakan sumber dan jangan reka fakta yang tiada.',
            'capabilities': ['chat', 'file_ingestion', 'chunking', 'rag', 'file_output'],
            'chunking': {'enabled': True, 'strategy': 'recursive', 'chunk_size': 1000, 'chunk_overlap': 150},
        },
    },
    {
        'id': 'operations-assistant',
        'name': 'Pembantu Operasi',
        'description': 'Agent berbilang langkah untuk alat, pengetahuan, fail dan proses kerja yang tahan kegagalan.',
        'icon': 'workflow',
        'config': {
            'template': 'operations-assistant',
            'instructions': 'Rancang sebelum bertindak, gunakan alat yang dibenarkan sahaja dan ringkaskan hasil setiap langkah.',
            'capabilities': ['chat', 'tools', 'rag', 'file_output'],
        },
    },
    {
        'id': 'custom-python',
        'name': 'Agent Python Tersuai',
        'description': 'Muat naik kod Python sendiri dan jalankannya melalui worker Temporal yang diasingkan.',
        'icon': 'code',
        'config': {
            'template': 'custom-python',
            'instructions': 'Ikut kontrak input/output agent dan hasilkan output JSON yang boleh diaudit.',
            'capabilities': ['custom_code', 'file_ingestion', 'file_output'],
            'runtime': {'mode': 'python', 'entrypoint': 'run', 'allow_network': False, 'memory_mb': 512},
        },
    },
]


class AgentImportForm(BaseModel):
    agents: list[AgentForm] = Field(min_length=1, max_length=100)


class WhisperInstallForm(BaseModel):
    model: str = Field(min_length=1, max_length=180)


class AgentRunForm(BaseModel):
    payload: dict = Field(default_factory=dict)


class ExternalAgentRunForm(BaseModel):
    message: str = Field(min_length=1, max_length=100000)
    session_key: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ComponentInstallForm(BaseModel):
    variant: Optional[str] = Field(default=None, max_length=200)
    access_token: Optional[str] = Field(default=None, max_length=500)
    accept_terms: bool = False


def _component_status(component: dict, active_whisper: str) -> dict:
    package = component.get('package')
    try:
        dependency_ready = package is None or importlib.util.find_spec(package) is not None
    except ModuleNotFoundError:
        dependency_ready = False
    installed = dependency_ready
    if component.get('custom'):
        installed = False
    elif component['id'] == 'whisper-stt':
        model_repo = active_whisper if '/' in active_whisper else f'Systran/faster-whisper-{active_whisper}'
        try:
            from huggingface_hub import try_to_load_from_cache

            installed = dependency_ready and try_to_load_from_cache(model_repo, 'config.json') is not None
        except Exception:
            installed = False
    elif component['id'] in {'pyannote-diarization', 'blip-vision', 'speechbrain-diarization'}:
        try:
            from huggingface_hub import try_to_load_from_cache

            marker = 'hyperparams.yaml' if component['id'] == 'speechbrain-diarization' else 'config.json'
            installed = dependency_ready and try_to_load_from_cache(component['default_variant'], marker) is not None
        except Exception:
            installed = False
    detail = 'Sedia digunakan' if installed else f'Pakej {component.get("package_spec", package)} belum dipasang'
    if component['id'] == 'whisper-stt':
        detail = f'Model tersedia: {active_whisper}' if installed else f'Model {active_whisper} belum dimuat turun'
    elif component.get('custom'):
        detail = 'Gunakan tab Kod Python untuk membina komponen sendiri'
    elif dependency_ready and not installed:
        detail = 'Model belum dimuat turun'
    return {**component, 'installed': installed, 'dependency_ready': dependency_ready, 'status_detail': detail}


def merge_template_config(config: dict) -> dict:
    defaults = AgentForm(name='Template').config.model_dump()
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            defaults[key] = {**defaults[key], **value}
        else:
            defaults[key] = value
    return defaults


def validate_python_source(source: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {'valid': False, 'errors': [f'Syntax error at line {exc.lineno}: {exc.msg}'], 'warnings': []}

    entrypoints = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entrypoints.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [alias.name.split('.')[0] for alias in node.names]
                if isinstance(node, ast.Import)
                else [(node.module or '').split('.')[0]]
            )
            for module in modules:
                if module in DANGEROUS_IMPORTS:
                    errors.append(f'Import "{module}" is not allowed in an agent package')
                elif module == 'os':
                    warnings.append('The os module is restricted by the worker runtime')
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else None
            if name in DANGEROUS_CALLS:
                errors.append(f'Call to "{name}" is not allowed')

    if 'run' not in entrypoints:
        errors.append('Agent code must define def run(context, payload) or async def run(context, payload)')

    return {'valid': not errors, 'errors': sorted(set(errors)), 'warnings': sorted(set(warnings))}


async def temporal_status() -> dict:
    enabled = os.getenv('TEMPORAL_ENABLED', 'false').lower() == 'true'
    address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
    namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    result = {'enabled': enabled, 'connected': False, 'address': address, 'namespace': namespace}
    if not enabled:
        result['message'] = 'Set TEMPORAL_ENABLED=true after starting a Temporal server.'
        return result

    try:
        from temporalio.client import Client

        tls = os.getenv('TEMPORAL_TLS', 'false').lower() == 'true'
        api_key = os.getenv('TEMPORAL_API_KEY', '')
        kwargs = {'namespace': namespace, 'tls': tls}
        if api_key:
            kwargs['api_key'] = api_key
        client = await asyncio.wait_for(Client.connect(address, **kwargs), timeout=4)
        await asyncio.wait_for(client.service_client.check_health(), timeout=4)
        result['connected'] = True
        result['message'] = 'Temporal connection is healthy.'
    except Exception as exc:
        result['message'] = f'Temporal is configured but unavailable: {exc}'
    return result


async def storage_status() -> dict:
    result = {
        'provider': STORAGE_PROVIDER,
        'connected': STORAGE_PROVIDER == 'local',
        'bucket': S3_BUCKET_NAME if STORAGE_PROVIDER == 's3' else None,
        'endpoint': S3_ENDPOINT_URL if STORAGE_PROVIDER == 's3' else None,
    }
    if STORAGE_PROVIDER != 's3':
        result['message'] = 'Local storage is active. Set STORAGE_PROVIDER=s3 to use MinIO.'
        return result
    try:
        await asyncio.wait_for(asyncio.to_thread(Storage.s3_client.head_bucket, Bucket=S3_BUCKET_NAME), timeout=4)
        result['connected'] = True
        result['message'] = 'MinIO/S3 bucket is reachable.'
    except Exception as exc:
        result['message'] = f'MinIO/S3 is configured but unavailable: {exc}'
    return result


@router.get('/templates')
async def get_agent_templates(user=Depends(get_admin_user)):
    return [{**item, 'config': merge_template_config(item['config'])} for item in AGENT_TEMPLATES]


@router.get('/platform/status')
async def get_agent_platform_status(request: Request, user=Depends(get_admin_user)):
    temporal, storage = await asyncio.gather(temporal_status(), storage_status())
    return {
        'temporal': temporal,
        'storage': storage,
        'whisper': {
            'active_model': request.app.state.config.WHISPER_MODEL,
            'model_directory': str(WHISPER_MODEL_DIR),
            'available_models': WHISPER_MODELS,
        },
        'default_task_queue': os.getenv('TEMPORAL_TASK_QUEUE', 'pengurusan-ai-agents'),
    }


@router.get('/components')
async def get_ai_components(request: Request, user=Depends(get_admin_user)):
    return [_component_status(component, request.app.state.config.WHISPER_MODEL) for component in AI_COMPONENTS]


@router.post('/components/{component_id}/install')
async def install_ai_component(
    component_id: str,
    request: Request,
    form: ComponentInstallForm,
    user=Depends(get_admin_user),
):
    component = next((item for item in AI_COMPONENTS if item['id'] == component_id), None)
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='AI component not found')
    if component.get('custom'):
        return {'success': True, 'component': _component_status(component, request.app.state.config.WHISPER_MODEL)}

    variant = form.variant or component['default_variant']
    if variant not in component['variants']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported component variant')
    if component.get('requires_terms') and not form.accept_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='You must accept the model terms before installation'
        )
    if component.get('requires_token') and not form.access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A Hugging Face access token is required')

    try:
        if component_id == 'whisper-stt':
            loaded_model = await asyncio.to_thread(set_faster_whisper_model, variant, True)
            request.app.state.faster_whisper_model = loaded_model
            request.app.state.config.WHISPER_MODEL = variant
        elif component_id == 'pyannote-diarization':
            try:
                pyannote_ready = importlib.util.find_spec('pyannote.audio') is not None
            except ModuleNotFoundError:
                pyannote_ready = False
            if not pyannote_ready:
                await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, '-m', 'pip', 'install', component['package_spec']],
                    check=True,
                )
            from pyannote.audio import Pipeline

            await asyncio.to_thread(Pipeline.from_pretrained, variant, token=form.access_token)
        elif component_id == 'speechbrain-diarization':
            for package_spec in component['package_specs']:
                await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, '-m', 'pip', 'install', package_spec],
                    check=True,
                )
            from speechbrain.inference.speaker import EncoderClassifier

            await asyncio.to_thread(EncoderClassifier.from_hparams, source=variant, run_opts={'device': 'cpu'})
        elif component_id == 'blip-vision':
            from transformers import AutoModelForMultimodalLM, AutoProcessor

            await asyncio.to_thread(AutoProcessor.from_pretrained, variant)
            await asyncio.to_thread(AutoModelForMultimodalLM.from_pretrained, variant)
        elif component_id == 'rapidocr':
            from rapidocr_onnxruntime import RapidOCR

            await asyncio.to_thread(RapidOCR)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Package installation failed: {exc}')
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Component installation failed: {exc}')

    importlib.invalidate_caches()
    return {
        'success': True,
        'component': _component_status(component, request.app.state.config.WHISPER_MODEL),
        'message': f'{component["name"]} is ready.',
    }


@router.get('/', response_model=list[AgentModel])
async def list_agents(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    return await AgentConfigurations.list(db=db)


@router.get('/openclaw/status')
async def get_openclaw_status(user=Depends(get_admin_user)):
    return await openclaw.status()


@router.post('/openclaw/sync', response_model=list[AgentModel])
async def sync_openclaw_agents(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    if not openclaw.enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='OpenClaw is not enabled')
    try:
        entries = await openclaw.list_agents()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to list OpenClaw agents: {exc}')

    synced: list[AgentModel] = []
    openclaw_ids: set[str] = set()
    for entry in entries:
        identifier = str(entry.get('id') or '').strip()
        if not identifier:
            continue
        openclaw_ids.add(identifier)
        identity = entry.get('identity') if isinstance(entry.get('identity'), dict) else {}
        existing = await AgentConfigurations.get_by_openclaw_id(identifier, db=db)
        if existing:
            config = existing.config.model_copy(deep=True)
            config.openclaw.agent_id = identifier
            config.openclaw.workspace = str(entry.get('workspace') or config.openclaw.workspace)
            config.model.model_id = str(entry.get('model') or config.model.model_id)
            config.model.provider = openclaw.model_provider(config.model.model_id)
            name = str(entry.get('name') or identity.get('name') or existing.name or identifier)
            updated = await AgentConfigurations.update(
                existing.id,
                AgentForm(
                    name=name,
                    description=existing.description,
                    config=config,
                    is_active=existing.is_active,
                ),
                db=db,
            )
            if updated:
                synced.append(updated)
            continue

        display_name = str(entry.get('name') or identity.get('name') or identifier)
        if len(display_name) < 2:
            display_name = f'Agent {identifier}'
        config = AgentForm(name=display_name).config
        config.model.model_id = str(entry.get('model') or '')
        config.model.provider = openclaw.model_provider(config.model.model_id)
        config.openclaw.agent_id = identifier
        config.openclaw.workspace = str(entry.get('workspace') or '')
        synced.append(
            await AgentConfigurations.insert(
                user.id,
                AgentForm(
                    name=display_name,
                    description=f'OpenClaw agent: {identifier}',
                    config=config,
                    is_active=False,
                ),
                db=db,
            )
        )

    for local_agent in await AgentConfigurations.list(db=db):
        identifier = local_agent.config.openclaw.agent_id
        if identifier and identifier not in openclaw_ids:
            await AgentConfigurations.update_settings(
                local_agent.id,
                local_agent.config.model.model_id or 'unconfigured',
                False,
                local_agent.config.model.provider,
                db=db,
            )
            if local_agent.api_key_configured:
                await AgentConfigurations.revoke_api_key(local_agent.id, db=db)
    return synced


@router.get('/export', response_model=list[AgentModel])
async def export_agents(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    return await AgentConfigurations.list(db=db)


@router.post('/import', response_model=list[AgentModel])
async def import_agents(
    form: AgentImportForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    return [await AgentConfigurations.insert(user.id, item, db=db) for item in form.agents]


@router.post('/create', response_model=AgentModel)
async def create_agent(form: AgentForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail='Create agents in OpenClaw, then use Sync OpenClaw in Konfigurasi Agent.',
    )


@router.get('/workflows/{workflow_id}/status')
async def get_agent_workflow_status(workflow_id: str, user=Depends(get_admin_user)):
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to query Temporal workflow: {exc}')


@router.get('/{agent_id}', response_model=AgentModel)
async def get_agent(agent_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    agent = await AgentConfigurations.get(agent_id, db=db)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    return agent


@router.post('/{agent_id}/update', response_model=AgentModel)
async def update_agent(
    agent_id: str, form: AgentForm, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail='Agent definitions are managed in OpenClaw. Only model and active status can be changed here.',
    )


@router.post('/{agent_id}/settings', response_model=AgentModel)
async def update_agent_settings(
    agent_id: str,
    form: AgentSettingsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    existing = await AgentConfigurations.get(agent_id, db=db)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    identifier = existing.config.openclaw.agent_id
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='This record is not linked to an OpenClaw agent. Sync OpenClaw first.',
        )
    if not openclaw.enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='OpenClaw is not enabled')
    model_id = existing.config.model.model_id or form.model_id
    if form.model_type == 'llm':
        try:
            model_id = await openclaw.configure_agent_model(identifier, form.model_id, form.provider)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to update OpenClaw model: {exc}'
            )
    updated = await AgentConfigurations.update_settings(
        agent_id,
        model_id,
        form.is_active,
        openclaw.model_provider(model_id),
        form.model_type,
        form.stt_model,
        db=db,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    return updated


@router.post('/{agent_id}/api-key/rotate')
async def rotate_agent_api_key(
    agent_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    existing = await AgentConfigurations.get(agent_id, db=db)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    if not existing.config.openclaw.agent_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Sync this agent from OpenClaw first')
    api_key = f'pai_{secrets.token_urlsafe(32)}'
    key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    prefix = api_key[:12]
    await AgentConfigurations.set_api_key(agent_id, key_hash, prefix, db=db)
    return {
        'api_key': api_key,
        'prefix': prefix,
        'message': 'Copy this key now. It cannot be shown again.',
    }


@router.delete('/{agent_id}/api-key', response_model=AgentModel)
async def revoke_agent_api_key(
    agent_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    updated = await AgentConfigurations.revoke_api_key(agent_id, db=db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    return updated


@router.post('/external/{agent_id}/invoke')
async def invoke_external_agent(
    agent_id: str,
    form: ExternalAgentRunForm,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_async_session),
):
    if os.getenv('AGENT_EXTERNAL_API_ENABLED', 'true').lower() != 'true':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='External agent API is disabled')
    scheme, _, token = (authorization or '').partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Bearer API key required')
    key_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    agent = await AgentConfigurations.authenticate_api_key(agent_id, key_hash, db=db)
    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid agent API key')
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Agent is inactive')
    identifier = agent.config.openclaw.agent_id
    if not identifier:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Agent is not linked to OpenClaw')
    try:
        result = await invoke_openclaw_via_temporal(
            agent,
            form.message.strip(),
            session_key=form.session_key,
        )
        return {
            'agent_id': identifier,
            'status': 'completed',
            'result': result,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Temporal agent run failed: {exc}')


@router.post('/{agent_id}/run')
async def run_agent(
    agent_id: str,
    form: AgentRunForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    agent = await AgentConfigurations.get(agent_id, db=db)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Activate the agent before running it')
    is_temporal_media_run = agent.config.orchestration.workflow_name == ASR_WORKFLOW_NAME and bool(
        form.payload.get('file_path') or form.payload.get('input_object_key')
    )
    input_file = form.payload.get('file_path') or form.payload.get('input_object_key')
    if agent.config.framework == 'openclaw' and agent.config.openclaw.agent_id and not is_temporal_media_run:
        message = form.payload.get('message') or form.payload.get('prompt') or form.payload.get('text')
        if not isinstance(message, str) or not message.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='OpenClaw runs require payload.message')
        try:
            return await invoke_openclaw_via_temporal(
                agent,
                message.strip(),
                session_key=form.payload.get('session_key'),
                user_id=user.id,
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Temporal agent run failed: {exc}')
    if agent.config.orchestration.engine != 'temporal':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Durable agent execution requires the Temporal orchestration engine.',
        )
    if os.getenv('TEMPORAL_ENABLED', 'false').lower() != 'true':
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Temporal is not enabled')

    try:
        from temporalio.client import Client

        address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
        namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
        tls = os.getenv('TEMPORAL_TLS', 'false').lower() == 'true'
        api_key = os.getenv('TEMPORAL_API_KEY', '') or None
        client = await Client.connect(address, namespace=namespace, tls=tls, api_key=api_key)
        workflow_id = f'agent-{agent.id}-{uuid4().hex}'
        workflow_name = agent.config.orchestration.workflow_name
        workflow_input = {
            'agent_id': agent.id,
            'payload': form.payload,
            'timeout_seconds': agent.config.orchestration.timeout_seconds,
            'max_retries': agent.config.orchestration.max_retries,
        }
        if agent.config.orchestration.workflow_name == ASR_WORKFLOW_NAME:
            file_path = input_file
            if not file_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail='Voice workflow requires payload.file_path'
                )
            bucket = agent.config.storage.bucket or S3_BUCKET_NAME
            object_key = file_path
            if file_path.startswith('s3://'):
                without_scheme = file_path.removeprefix('s3://')
                uri_bucket, _, object_key = without_scheme.partition('/')
                bucket = uri_bucket or bucket
            workflow_input = {
                'jobId': form.payload.get('job_id') or f'agent-{agent.id}-{uuid4().hex}',
                'inputObjectKey': object_key,
                'mediaTaskQueue': agent.config.orchestration.media_task_queue,
                'asrTaskQueue': agent.config.orchestration.asr_task_queue,
                'targetBucket': bucket,
            }

        handle = await client.start_workflow(
            workflow_name,
            workflow_input,
            id=workflow_id,
            task_queue=agent.config.orchestration.task_queue,
            execution_timeout=timedelta(seconds=agent.config.orchestration.timeout_seconds),
        )
        return {'started': True, 'workflow_id': handle.id, 'run_id': handle.result_run_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to start Temporal workflow: {exc}')


@router.delete('/{agent_id}')
async def delete_agent(agent_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail='Delete the agent in OpenClaw, then synchronize the registry.',
    )


@router.post('/{agent_id}/code', response_model=AgentModel)
async def upload_agent_code(
    agent_id: str,
    file: UploadFile = File(...),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not file.filename or Path(file.filename).suffix.lower() != '.py':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only .py files are accepted')
    contents = await file.read(MAX_AGENT_CODE_BYTES + 1)
    if len(contents) > MAX_AGENT_CODE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail='Agent code must be 512 KB or smaller'
        )
    try:
        source = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Agent code must be UTF-8 text')

    validation = validate_python_source(source)
    if not validation['valid']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={'message': 'Agent code failed validation', **validation}
        )

    if not await AgentConfigurations.get(agent_id, db=db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found')

    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', Path(file.filename).name)
    object_name = f'agent-{agent_id}-{uuid4().hex}-{safe_filename}'
    _, code_path = await asyncio.to_thread(
        Storage.upload_file,
        io.BytesIO(contents),
        object_name,
        {'resource': 'agent-code', 'agent_id': agent_id},
    )
    digest = hashlib.sha256(contents).hexdigest()
    result = await AgentConfigurations.set_code(agent_id, code_path, safe_filename, digest, validation, db=db)
    agent, old_path = result
    if old_path and old_path != code_path:
        try:
            await asyncio.to_thread(Storage.delete_file, old_path)
        except Exception:
            pass
    return agent


@router.post('/models/whisper/install')
async def install_whisper_model(
    request: Request,
    form: WhisperInstallForm,
    user=Depends(get_admin_user),
):
    model = form.model.strip()
    if model not in WHISPER_MODELS and not re.fullmatch(r'[\w.-]+/[\w.-]+', model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Use an official Whisper size or a Hugging Face repository in owner/model format.',
        )
    try:
        loaded_model = await asyncio.to_thread(set_faster_whisper_model, model, True)
        request.app.state.faster_whisper_model = loaded_model
        request.app.state.config.WHISPER_MODEL = model
        return {'success': True, 'model': model, 'message': 'Whisper model installed and activated.'}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Unable to install Whisper model: {exc}')


@router.get('/code/template/python')
async def get_python_agent_template(user=Depends(get_admin_user)):
    return {
        'filename': 'my_agent.py',
        'content': '''async def run(context, payload):\n    """Temporal worker entrypoint for a Pengurusan AI agent."""\n    context.log("Agent started")\n    text = payload.get("text", "")\n    return {"status": "completed", "output": text}\n''',
    }
