import asyncio
import json
import os
import re
import shutil
from pathlib import Path

from open_webui.env import DATA_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_configured_models: set[str] = set()
_configured_agent_runtimes: set[tuple[str, str]] = set()
_provider_lock = asyncio.Lock()


def _configured_path(variable: str, fallback: Path) -> Path:
    value = Path(os.getenv(variable, str(fallback))).expanduser()
    return (PROJECT_ROOT / value).resolve() if not value.is_absolute() else value.resolve()


def enabled() -> bool:
    return os.getenv('OPENCLAW_ENABLED', 'false').lower() == 'true'


def command() -> str:
    configured = os.getenv('OPENCLAW_COMMAND')
    if configured:
        return configured
    local_cli = PROJECT_ROOT / 'node_modules' / '.bin' / 'openclaw'
    return str(local_cli) if local_cli.exists() else 'openclaw'


def state_dir() -> Path:
    return _configured_path('OPENCLAW_STATE_DIR', Path(DATA_DIR) / 'openclaw')


def workspace_root() -> Path:
    return _configured_path('OPENCLAW_WORKSPACE_ROOT', state_dir() / 'workspaces')


def normalize_model_reference(model: str, provider: str | None = None) -> str:
    """Convert platform model IDs into provider-qualified OpenClaw refs."""
    reference = model.strip()
    if not reference or '/' in reference:
        return reference
    normalized_provider = (provider or '').strip().lower()
    if normalized_provider == 'ollama' or ':' in reference:
        return f'ollama/{reference}'
    if normalized_provider and normalized_provider not in {'platform', 'local', 'unknown'}:
        return f'{normalized_provider}/{reference}'
    return reference


def model_provider(model: str) -> str:
    """Return the provider value supported by AgentModelConfig."""
    return 'ollama' if normalize_model_reference(model).startswith('ollama/') else 'platform'


async def ensure_model_provider(model: str) -> None:
    """Ensure local providers selected in Pengurusan AI exist in OpenClaw."""
    provider, separator, _ = model.partition('/')
    if not separator or model in _configured_models:
        return
    async with _provider_lock:
        if model in _configured_models:
            return
        if provider == 'ollama':
            model_id = model.removeprefix('ollama/')
            config_path = state_dir() / 'openclaw.json'
            try:
                config = json.loads(config_path.read_text(encoding='utf-8'))
            except (FileNotFoundError, json.JSONDecodeError):
                config = {}
            existing = config.get('models', {}).get('providers', {}).get('ollama', {})
            existing_models = existing.get('models') if isinstance(existing, dict) else []
            configured_models = [item for item in (existing_models or []) if isinstance(item, dict)]
            num_ctx = max(4096, int(os.getenv('OPENCLAW_OLLAMA_NUM_CTX', '16384')))
            model_config = next((item for item in configured_models if item.get('id') == model_id), None)
            if model_config is None:
                model_config = {'id': model_id, 'name': model_id}
                configured_models.append(model_config)
            model_config['contextWindow'] = num_ctx
            model_config['maxTokens'] = min(8192, max(1024, num_ctx // 2))
            model_config['params'] = {
                **(model_config.get('params') if isinstance(model_config.get('params'), dict) else {}),
                'num_ctx': num_ctx,
                'keep_alive': '15m',
            }
            ollama_key = os.getenv('OLLAMA_API_KEY', '').strip()
            provider_config = {
                **(existing if isinstance(existing, dict) else {}),
                'baseUrl': os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/'),
                'apiKey': (
                    'OLLAMA_API_KEY' if ollama_key and ollama_key != 'ollama-local' else 'ollama-local'
                ),
                'api': 'ollama',
                'models': configured_models,
            }
            await _run('config', 'set', 'plugins.entries.ollama.enabled', 'true')
            await _run(
                'config',
                'set',
                'models.providers.ollama',
                json.dumps(provider_config, separators=(',', ':')),
                '--strict-json',
            )
        _configured_models.add(model)


def _workspace_disables_tools(workspace: str) -> bool:
    try:
        content = (Path(workspace) / 'TOOLS.md').read_text(encoding='utf-8').lower()
    except (OSError, UnicodeError):
        return False
    return any(
        marker in content
        for marker in ('tiada alat luaran didayakan', 'no external tools are enabled')
    )


async def ensure_agent_runtime(identifier: str, model: str, entries: list[dict] | None = None) -> None:
    """Keep local-model prompts small and enforce workspace-declared no-tool agents."""
    runtime_key = (identifier, model)
    if runtime_key in _configured_agent_runtimes:
        return
    entries = entries if entries is not None else await list_agents()
    index = next((position for position, item in enumerate(entries) if item.get('id') == identifier), None)
    if index is None:
        raise RuntimeError(f'OpenClaw agent {identifier} is not registered')
    prefix = f'agents.list[{index}]'
    if model.startswith('ollama/'):
        await _run('config', 'set', f'{prefix}.experimental.localModelLean', 'true')
    if _workspace_disables_tools(str(entries[index].get('workspace') or '')):
        await _run('config', 'set', f'{prefix}.tools.profile', 'minimal')
    _configured_agent_runtimes.add(runtime_key)


def _environment() -> dict[str, str]:
    target = state_dir()
    target.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['OPENCLAW_HOME'] = str(target)
    env['OPENCLAW_STATE_DIR'] = str(target)
    env['OPENCLAW_CONFIG_PATH'] = str(target / 'openclaw.json')
    env['NO_COLOR'] = '1'
    # OpenClaw only registers its implicit local Ollama provider when this
    # marker (or an auth profile) exists. It is not a real credential.
    if not env.get('OLLAMA_API_KEY'):
        env['OLLAMA_API_KEY'] = 'ollama-local'
    return env


async def _run(*arguments: str, timeout: int = 120) -> dict:
    executable = shutil.which(command())
    if not executable:
        raise RuntimeError('OpenClaw CLI is not installed. Run make openclaw-setup first.')
    process = await asyncio.create_subprocess_exec(
        executable,
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_environment(),
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
    except TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError('OpenClaw command timed out')
    if process.returncode != 0:
        message = stderr.decode(errors='replace').strip() or stdout.decode(errors='replace').strip()
        raise RuntimeError(message or f'OpenClaw exited with status {process.returncode}')
    output = stdout.decode(errors='replace').strip()
    try:
        return json.loads(output) if output else {'success': True}
    except json.JSONDecodeError:
        return {'success': True, 'output': output}


def agent_id(agent_uuid: str) -> str:
    return f'pengurusan-{re.sub(r"[^a-z0-9]", "", agent_uuid.lower())[:16]}'


def prepare_workspace(agent_uuid: str, name: str, instructions: str) -> Path:
    root = workspace_root()
    root.mkdir(parents=True, exist_ok=True)
    workspace = (root / agent_id(agent_uuid)).resolve()
    if root not in workspace.parents:
        raise RuntimeError('Invalid OpenClaw workspace path')
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / 'IDENTITY.md').write_text(f'# Identity\n\nName: {name}\n', encoding='utf-8')
    (workspace / 'SOUL.md').write_text(
        f'# Purpose and behaviour\n\n{instructions.strip() or "Be helpful, accurate, and safe."}\n',
        encoding='utf-8',
    )
    (workspace / 'AGENTS.md').write_text(
        '# Pengurusan AI contract\n\nFollow the configured permissions. Do not expose secrets. '
        'Store durable file artifacts through the Pengurusan AI workflow and MinIO services.\n',
        encoding='utf-8',
    )
    return workspace


def write_temporal_contract(workspace: str, orchestration: dict, storage: dict) -> None:
    target = Path(workspace).resolve()
    root = workspace_root()
    if root != target and root not in target.parents:
        raise RuntimeError('Invalid OpenClaw workspace path')
    workflow = orchestration.get('workflow_name', '')
    if workflow != os.getenv('TEMPORAL_ASR_WORKFLOW', 'AsrWorkflow::start'):
        return
    (target / 'TOOLS.md').write_text(
        '# Durable media workflow\n\n'
        'Audio and video files are processed by the Pengurusan AI host through Temporal. '
        'Do not transcribe large media inside the conversational agent process.\n\n'
        f'- Workflow: `{workflow}`\n'
        f'- Workflow queue: `{orchestration.get("task_queue", "ASR_WORKFLOW_QUEUE")}`\n'
        f'- Media queue: `{orchestration.get("media_task_queue", "MEDIA_TASK_QUEUE")}`\n'
        f'- ASR queue: `{orchestration.get("asr_task_queue", "ASR_TASK_QUEUE")}`\n'
        f'- MinIO bucket: `{storage.get("bucket") or "platform default"}`\n\n'
        'Pipeline: normalize -> overlapping audio chunks -> Whisper ASR -> speaker diarization -> '
        'speaker refinement -> merged transcript -> summary -> thematic analysis -> JSON/SRT/VTT and chunks in MinIO.\n',
        encoding='utf-8',
    )


async def status() -> dict:
    installed = shutil.which(command()) is not None
    result = {
        'enabled': enabled(),
        'installed': installed,
        'command': command(),
        'state_dir': str(state_dir()),
        'connected': False,
    }
    if not installed:
        result['message'] = 'OpenClaw CLI is not installed.'
        return result
    if not enabled():
        result['message'] = 'Set OPENCLAW_ENABLED=true after OpenClaw onboarding.'
        return result
    try:
        agents = await _run('agents', 'list', '--json', timeout=20)
        result['connected'] = True
        result['agents'] = agents
        result['message'] = 'OpenClaw agent registry is ready.'
    except Exception as exc:
        result['message'] = f'OpenClaw is unavailable: {exc}'
    return result


async def list_agents() -> list[dict]:
    result = await _run('agents', 'list', '--json', timeout=30)
    entries = result if isinstance(result, list) else result.get('agents', [])
    return entries if isinstance(entries, list) else []


async def configure_agent(identifier: str, model: str, thinking: str, sandbox: bool) -> None:
    entries = await list_agents()
    index = next((position for position, item in enumerate(entries) if item.get('id') == identifier), None)
    if index is None:
        raise RuntimeError(f'OpenClaw agent {identifier} is not registered')
    prefix = f'agents.list[{index}]'
    await _run('config', 'set', f'{prefix}.model', model)
    await _run('config', 'set', f'{prefix}.thinkingDefault', thinking)
    await _run('config', 'set', f'{prefix}.sandbox.mode', 'all' if sandbox else 'off')


async def configure_agent_model(identifier: str, model: str, provider: str | None = None) -> str:
    model = normalize_model_reference(model, provider)
    await ensure_model_provider(model)
    entries = await list_agents()
    index = next((position for position, item in enumerate(entries) if item.get('id') == identifier), None)
    if index is None:
        raise RuntimeError(f'OpenClaw agent {identifier} is not registered')
    await _run('config', 'set', f'agents.list[{index}].model', model)
    await ensure_agent_runtime(identifier, model, entries)
    return model


async def register_agent(
    agent_uuid: str, name: str, instructions: str, model: str, thinking: str = 'medium', sandbox: bool = True
) -> dict:
    workspace = prepare_workspace(agent_uuid, name, instructions)
    identifier = agent_id(agent_uuid)
    result = await _run(
        'agents', 'add', identifier,
        '--workspace', str(workspace),
        '--model', model,
        '--non-interactive',
        '--json',
    )
    await configure_agent(identifier, model, thinking, sandbox)
    return {'agent_id': identifier, 'workspace': str(workspace), 'result': result}


async def update_agent(
    identifier: str, workspace: str, name: str, instructions: str, model: str, thinking: str, sandbox: bool
) -> None:
    root = workspace_root()
    target = Path(workspace).resolve()
    if root != target and root not in target.parents:
        raise RuntimeError('Invalid OpenClaw workspace path')
    target.mkdir(parents=True, exist_ok=True)
    (target / 'IDENTITY.md').write_text(f'# Identity\n\nName: {name}\n', encoding='utf-8')
    (target / 'SOUL.md').write_text(
        f'# Purpose and behaviour\n\n{instructions.strip() or "Be helpful, accurate, and safe."}\n',
        encoding='utf-8',
    )
    await configure_agent(identifier, model, thinking, sandbox)


async def delete_agent(identifier: str) -> dict:
    return await _run('agents', 'delete', identifier, '--force', '--json')


async def invoke_agent(
    identifier: str,
    message: str,
    model: str,
    timeout: int = 600,
    session_key: str | None = None,
) -> dict:
    model = normalize_model_reference(model)
    await ensure_model_provider(model)
    await ensure_agent_runtime(identifier, model)
    arguments = ['agent', '--local', '--agent', identifier, '--message', message, '--model', model, '--json']
    if session_key:
        arguments.extend(['--session-key', session_key])
    return await _run(*arguments, timeout=timeout)
