from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from open_webui.models.users import UserModel
from open_webui.retrieval.utils import get_sources_from_items


class RetrievalGraphState(TypedDict, total=False):
    request: Any
    items: list[dict[str, Any]]
    queries: list[str]
    embedding_function: Any
    k: int
    reranking_function: Any
    k_reranker: int
    r: float
    hybrid_bm25_weight: float
    hybrid_search: bool
    full_context: bool
    user: UserModel | None
    sources: list[dict[str, Any]]


async def _retrieve_sources(state: RetrievalGraphState) -> RetrievalGraphState:
    sources = await get_sources_from_items(
        request=state['request'],
        items=state.get('items', []),
        queries=state.get('queries', []),
        embedding_function=state['embedding_function'],
        k=state['k'],
        reranking_function=state.get('reranking_function'),
        k_reranker=state['k_reranker'],
        r=state['r'],
        hybrid_bm25_weight=state['hybrid_bm25_weight'],
        hybrid_search=state.get('hybrid_search', False),
        full_context=state.get('full_context', False),
        user=state.get('user'),
    )
    return {**state, 'sources': sources}


def build_retrieval_graph():
    graph = StateGraph(RetrievalGraphState)
    graph.add_node('retrieve_sources', _retrieve_sources)
    graph.add_edge(START, 'retrieve_sources')
    graph.add_edge('retrieve_sources', END)
    return graph.compile()


RETRIEVAL_GRAPH = build_retrieval_graph()


async def run_retrieval_graph(**kwargs) -> list[dict[str, Any]]:
    result = await RETRIEVAL_GRAPH.ainvoke(kwargs)
    return result.get('sources', [])
