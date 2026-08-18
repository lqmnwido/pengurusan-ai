import { WEBUI_API_BASE_URL } from '$lib/constants';
export type AgenticWorkflowNode = {
	agent_id: string;
	model_id: string;
	instruction: string;
};

export type AgenticWorkflowConfig = {
	engine: string;
	trigger: string;
	task_queue: string;
	timeout_seconds: number;
	max_retries: number;
	nodes: AgenticWorkflowNode[];
	visible_in_chat: boolean;
	executor_agent_id: string;
	allowed_agent_ids: string[];
	flow?: unknown;
};

export type AgenticWorkflowForm = {
	name: string;
	description?: string | null;
	tool_name: string;
	config: AgenticWorkflowConfig;
	is_active: boolean;
};

export type AgenticWorkflow = AgenticWorkflowForm & {
	id: string;
	user_id: string;
	created_at: number;
	updated_at: number;
};

const request = async (token: string, path: string, options: RequestInit = {}) => {
	const headers = new Headers(options.headers);
	headers.set('Accept', 'application/json');
	headers.set('authorization', `Bearer ${token}`);
	headers.set('Content-Type', 'application/json');
	const response = await fetch(`${WEBUI_API_BASE_URL}/agentic-workflows${path}`, {
		...options,
		headers
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: response.statusText }));
		throw typeof error?.detail === 'string' ? error.detail : JSON.stringify(error?.detail ?? error);
	}
	return response.json();
};

export const getAgenticWorkflows = (token: string): Promise<AgenticWorkflow[]> =>
	request(token, '/');

export const createAgenticWorkflow = (
	token: string,
	form: AgenticWorkflowForm
): Promise<AgenticWorkflow> =>
	request(token, '/create', { method: 'POST', body: JSON.stringify(form) });

export const updateAgenticWorkflow = (
	token: string,
	id: string,
	form: AgenticWorkflowForm
): Promise<AgenticWorkflow> =>
	request(token, `/${id}/update`, { method: 'POST', body: JSON.stringify(form) });

export const deleteAgenticWorkflow = (token: string, id: string) =>
	request(token, `/${id}`, { method: 'DELETE' });

export const runAgenticWorkflow = (token: string, id: string, message: string, jobId?: string) =>
	request(token, `/${id}/run`, {
		method: 'POST',
		body: JSON.stringify({ message, job_id: jobId || null })
	});

export const getAgenticWorkflowRunStatus = (token: string, workflowId: string) =>
	request(token, `/runs/${encodeURIComponent(workflowId)}/status`);
