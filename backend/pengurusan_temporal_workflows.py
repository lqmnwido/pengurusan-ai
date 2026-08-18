"""Deterministic Temporal workflows for Pengurusan AI.

Keep this module independent from the ``open_webui`` package. Temporal imports
workflow modules inside its sandbox, while activities may use the full
application runtime outside the sandbox.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

OPENCLAW_CHAT_WORKFLOW = 'pengurusan_ai.openclaw.chat'
VOICE_FLOW_WORKFLOW = 'pengurusan_ai.voice.v2t'
AGENT_CHAIN_WORKFLOW = 'pengurusan_ai.agentic.chain'


@workflow.defn(name='pengurusan_ai.agent.run')
class PengurusanAgentWorkflow:
    @workflow.run
    async def run(self, input_data: dict):
        timeout = int(input_data.get('timeout_seconds', 900))
        return await workflow.execute_activity(
            'pengurusan_ai.execute_agent',
            input_data,
            result_type=dict,
            start_to_close_timeout=timedelta(seconds=timeout),
        )


@workflow.defn(name=OPENCLAW_CHAT_WORKFLOW)
class OpenClawChatWorkflow:
    @workflow.run
    async def run(self, input_data: dict):
        timeout = int(input_data.get('timeout_seconds', 900))
        return await workflow.execute_activity(
            'pengurusan_ai.openclaw.invoke',
            input_data,
            result_type=dict,
            start_to_close_timeout=timedelta(seconds=timeout),
            retry_policy=RetryPolicy(maximum_attempts=max(1, int(input_data.get('max_retries', 3)) + 1)),
        )


@workflow.defn(name=AGENT_CHAIN_WORKFLOW)
class AgenticChainWorkflow:
    def __init__(self):
        self._status = 'queued'
        self._current_step = None
        self._current_agent_name = None
        self._current_instruction = None
        self._progress = 0
        self._outputs = []

    @workflow.query
    def status(self) -> dict:
        return {
            'status': self._status,
            'current_step': self._current_step,
            'current_agent_name': self._current_agent_name,
            'current_instruction': self._current_instruction,
            'progress': self._progress,
            'outputs': self._outputs,
        }

    @workflow.run
    async def run(self, input_data: dict):
        retry_policy = RetryPolicy(maximum_attempts=max(1, int(input_data.get('max_retries', 3)) + 1))
        nodes = await workflow.execute_activity(
            'pengurusan_ai.langgraph.agent.plan',
            {'nodes': input_data['nodes']},
            result_type=list,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=retry_policy,
        )
        original_message = input_data['message']
        previous_output = ''
        self._status = 'running'
        for index, node in enumerate(nodes):
            self._current_step = node['agent_id']
            self._current_agent_name = node.get('agent_name') or node.get('openclaw_agent_id') or node['agent_id']
            self._current_instruction = node.get('instruction') or (
                'Memproses permintaan pengguna' if index == 0 else 'Memproses output daripada agent sebelumnya'
            )
            result = await workflow.execute_activity(
                'pengurusan_ai.openclaw.chain.node',
                {
                    **input_data,
                    'node': node,
                    'node_index': index,
                    'original_message': original_message,
                    'previous_output': previous_output,
                },
                result_type=dict,
                start_to_close_timeout=timedelta(seconds=int(input_data.get('timeout_seconds', 900))),
                retry_policy=retry_policy,
            )
            previous_output = result['text']
            self._outputs.append(result)
            self._progress = round((index + 1) / len(nodes) * 100)
        self._status = 'completed'
        self._current_step = None
        self._current_agent_name = None
        self._current_instruction = None
        return {'text': previous_output, **self.status()}


@workflow.defn(name=VOICE_FLOW_WORKFLOW)
class VoiceIntelligenceWorkflow:
    def __init__(self):
        self._status = 'queued'
        self._current_step = 'Menunggu worker'
        self._progress = 0
        self._completed_steps = 0
        self._total_steps = 0
        self._artifact_path = None
        self._error = None

    @workflow.query
    def status(self) -> dict:
        return {
            'status': self._status,
            'current_step': self._current_step,
            'progress': self._progress,
            'completed_steps': self._completed_steps,
            'total_steps': self._total_steps,
            'artifact_path': self._artifact_path,
            'error': self._error,
        }

    @workflow.run
    async def run(self, input_data: dict):
        timeout = int(input_data.get('timeout_seconds', 3600))
        retry_policy = RetryPolicy(maximum_attempts=max(1, int(input_data.get('max_retries', 3)) + 1))
        self._status = 'planning'
        self._current_step = 'LangGraph sedang membina aliran'
        try:
            plan = await workflow.execute_activity(
                'pengurusan_ai.langgraph.voice.plan',
                {'flow': input_data['flow']},
                result_type=list,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            self._total_steps = len(plan)
            state = {
                'agent_id': input_data['agent_id'],
                'agentic_workflow_id': input_data.get('agentic_workflow_id'),
                'job_id': input_data['job_id'],
                'input_file': input_data['input_file'],
                'artifact_path': None,
            }
            self._status = 'running'
            for index, stage in enumerate(plan):
                self._current_step = stage['component']
                state = await workflow.execute_activity(
                    'pengurusan_ai.langgraph.voice.node',
                    {'state': state, 'stage': stage},
                    result_type=dict,
                    start_to_close_timeout=timedelta(seconds=timeout),
                    heartbeat_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
                self._artifact_path = state.get('artifact_path')
                self._completed_steps = index + 1
                self._progress = round(self._completed_steps / self._total_steps * 100)
            self._status = 'completed'
            self._current_step = 'Selesai'
            return {**state, **self.status()}
        except Exception as exc:
            self._status = 'failed'
            self._error = str(exc)
            raise
