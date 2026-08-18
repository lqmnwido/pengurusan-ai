import { WEBUI_API_BASE_URL } from '$lib/constants';

export type AgentConfig = {
	framework: 'openclaw';
	template: string;
	instructions: string;
	capabilities: string[];
	tools: string[];
	knowledge_ids: string[];
	model: {
		kind: 'llm' | 'whisper';
		provider: string;
		model_id: string;
		stt_model: string;
		temperature: number;
		max_tokens: number;
	};
	orchestration: {
		engine: 'local' | 'temporal';
		workflow_name: string;
		task_queue: string;
		media_task_queue: string;
		asr_task_queue: string;
		timeout_seconds: number;
		max_retries: number;
	};
	storage: {
		provider: 'inherit' | 'minio' | 'local';
		bucket?: string | null;
		prefix: string;
		save_originals: boolean;
		save_outputs: boolean;
		retention_days: number;
	};
	chunking: {
		enabled: boolean;
		strategy: string;
		chunk_size: number;
		chunk_overlap: number;
		embedding_model: string;
	};
	runtime: {
		mode: 'builtin' | 'python';
		entrypoint: string;
		allow_network: boolean;
		memory_mb: number;
	};
	components: string[];
	openclaw: {
		agent_id: string;
		workspace: string;
		thinking: 'off' | 'minimal' | 'low' | 'medium' | 'high';
		sandbox: boolean;
	};
};

export type AgentFlowStage = {
	enabled: boolean;
	component: string;
	agent_id: string;
	provider: string;
	model_id: string;
	prompt: string;
	options: Record<string, string | number | boolean>;
};

export type AgentFlowConfig = {
	enabled: boolean;
	engine: 'langgraph';
	template: 'voice-intelligence-v1';
	stages: AgentFlowStage[];
};

export type AIComponent = {
	id: string;
	name: string;
	category: 'audio' | 'vision' | 'custom';
	description: string;
	capability: string;
	variants: string[];
	default_variant?: string | null;
	size_hint: string;
	installed: boolean;
	dependency_ready: boolean;
	status_detail: string;
	requires_token?: boolean;
	requires_terms?: boolean;
	custom?: boolean;
	reference_profile?: string;
};

export type AgentForm = {
	name: string;
	description?: string | null;
	config: AgentConfig;
	is_active: boolean;
};

export type Agent = AgentForm & {
	id: string;
	user_id: string;
	code_path?: string | null;
	code_filename?: string | null;
	code_sha256?: string | null;
	code_validation?: { valid: boolean; errors: string[]; warnings: string[] } | null;
	api_key_configured: boolean;
	api_key_prefix?: string | null;
	api_key_created_at?: number | null;
	api_key_last_used_at?: number | null;
	created_at: number;
	updated_at: number;
};

export type AgentTemplate = {
	id: string;
	name: string;
	description: string;
	icon: string;
	config: AgentConfig;
};

const request = async (token: string, path: string, options: RequestInit = {}) => {
	const headers = new Headers(options.headers);
	headers.set('Accept', 'application/json');
	headers.set('authorization', `Bearer ${token}`);
	if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');

	const response = await fetch(`${WEBUI_API_BASE_URL}/agents${path}`, { ...options, headers });
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: response.statusText }));
		const detail = error?.detail;
		throw typeof detail === 'string' ? detail : detail?.message || JSON.stringify(detail || error);
	}
	return response.json();
};

export const getAgents = (token: string): Promise<Agent[]> => request(token, '/');
export const getAgentTemplates = (token: string): Promise<AgentTemplate[]> =>
	request(token, '/templates');
export const getAgentPlatformStatus = (token: string) => request(token, '/platform/status');
export const getAIComponents = (token: string): Promise<AIComponent[]> =>
	request(token, '/components');
export const getOpenClawStatus = (token: string) => request(token, '/openclaw/status');
export const syncOpenClawAgents = (token: string): Promise<Agent[]> =>
	request(token, '/openclaw/sync', { method: 'POST' });
export const updateAgentSettings = (
	token: string,
	id: string,
	form: {
		model_id: string;
		provider?: string | null;
		model_type?: 'llm' | 'whisper';
		stt_model?: string | null;
		is_active: boolean;
	}
): Promise<Agent> =>
	request(token, `/${id}/settings`, { method: 'POST', body: JSON.stringify(form) });
export const rotateAgentApiKey = (
	token: string,
	id: string
): Promise<{ api_key: string; prefix: string; message: string }> =>
	request(token, `/${id}/api-key/rotate`, { method: 'POST' });
export const revokeAgentApiKey = (token: string, id: string): Promise<Agent> =>
	request(token, `/${id}/api-key`, { method: 'DELETE' });
export const createAgent = (token: string, form: AgentForm): Promise<Agent> =>
	request(token, '/create', { method: 'POST', body: JSON.stringify(form) });
export const updateAgent = (token: string, id: string, form: AgentForm): Promise<Agent> =>
	request(token, `/${id}/update`, { method: 'POST', body: JSON.stringify(form) });
export const deleteAgent = (token: string, id: string) =>
	request(token, `/${id}`, { method: 'DELETE' });
export const importAgents = (token: string, agents: AgentForm[]): Promise<Agent[]> =>
	request(token, '/import', { method: 'POST', body: JSON.stringify({ agents }) });
export const exportAgents = (token: string): Promise<Agent[]> => request(token, '/export');

export const uploadAgentCode = (token: string, id: string, file: File): Promise<Agent> => {
	const form = new FormData();
	form.append('file', file);
	return request(token, `/${id}/code`, { method: 'POST', body: form });
};

export const installWhisperModel = (token: string, model: string) =>
	request(token, '/models/whisper/install', { method: 'POST', body: JSON.stringify({ model }) });

export const installAIComponent = (
	token: string,
	id: string,
	form: { variant?: string; access_token?: string; accept_terms?: boolean }
) => request(token, `/components/${id}/install`, { method: 'POST', body: JSON.stringify(form) });

export const runAgent = (token: string, id: string, payload: Record<string, any> = {}) =>
	request(token, `/${id}/run`, { method: 'POST', body: JSON.stringify({ payload }) });

export const getAgentWorkflowStatus = (token: string, workflowId: string) =>
	request(token, `/workflows/${encodeURIComponent(workflowId)}/status`);
