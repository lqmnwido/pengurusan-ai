"""LangGraph topology for the configurable Voice Intelligence workflow.

LangGraph owns the graph definition. Temporal materialises the resulting plan
as durable activities so retries and progress remain visible in Temporal.
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


VOICE_COMPONENTS = {
    'faster-whisper',
    'pyannote-diarization',
    'speechbrain-diarization',
    'transcript-chunking',
    'openclaw-topic',
    'openclaw-summary',
    'openclaw-thematic',
}


def _append(left: list[dict], right: list[dict]) -> list[dict]:
    return [*left, *right]


class VoicePlanState(TypedDict, total=False):
    plan: Annotated[list[dict], _append]


def build_voice_flow_plan(flow: dict) -> list[dict]:
    """Compile and execute a deterministic LangGraph plan from saved settings."""
    stages = [stage for stage in flow.get('stages', []) if stage.get('enabled', True)]
    if not stages:
        raise ValueError('Enable at least one Voice Intelligence component')
    if any(stage.get('component') not in VOICE_COMPONENTS for stage in stages):
        raise ValueError('Voice Intelligence contains an unsupported component')
    if stages[0].get('component') != 'faster-whisper':
        raise ValueError('Voice Intelligence must begin with faster-whisper transcription')

    graph = StateGraph(VoicePlanState)
    previous = START
    for index, stage in enumerate(stages):
        node_name = f'{index:02d}-{stage["component"]}'

        def add_to_plan(_state: VoicePlanState, item=dict(stage)) -> VoicePlanState:
            return {'plan': [item]}

        graph.add_node(node_name, add_to_plan)
        graph.add_edge(previous, node_name)
        previous = node_name
    graph.add_edge(previous, END)
    result = graph.compile().invoke({'plan': []})
    return result['plan']
