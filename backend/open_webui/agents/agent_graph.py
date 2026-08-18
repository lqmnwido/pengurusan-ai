"""LangGraph compiler for ordered OpenClaw agent workflows."""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


def _append(left: list[dict], right: list[dict]) -> list[dict]:
    return [*left, *right]


class AgentPlanState(TypedDict, total=False):
    plan: Annotated[list[dict], _append]


def build_agent_chain_plan(nodes: list[dict]) -> list[dict]:
    if not nodes:
        raise ValueError('Add at least one OpenClaw agent to the workflow')
    graph = StateGraph(AgentPlanState)
    previous = START
    for index, node in enumerate(nodes):
        node_name = f'{index:03d}-{node["agent_id"]}'

        def add_to_plan(_state: AgentPlanState, item=dict(node)) -> AgentPlanState:
            return {'plan': [item]}

        graph.add_node(node_name, add_to_plan)
        graph.add_edge(previous, node_name)
        previous = node_name
    graph.add_edge(previous, END)
    return graph.compile().invoke({'plan': []})['plan']
