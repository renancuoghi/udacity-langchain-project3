from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from solution.agentic.agents.nodes import (
    classifier_agent,
    escalation_agent,
    intake_agent,
    knowledge_agent,
    memory_agent,
    resolver_agent,
    response_agent,
    router_agent,
    tool_agent,
)
from solution.agentic.state import TicketState

CONFIDENCE_THRESHOLD = 0.25


def _route_after_router(state: TicketState) -> str:
    return state.get("route", "knowledge_agent")


def _route_after_knowledge(state: TicketState) -> str:
    confidence = float(state.get("confidence", 0.0))
    has_articles = bool(state.get("retrieved_articles"))
    if has_articles and confidence >= CONFIDENCE_THRESHOLD:
        return "resolver_agent"
    return "escalation_agent"


def build_workflow():
    graph = StateGraph(TicketState)

    graph.add_node("intake_agent", intake_agent)
    graph.add_node("classifier_agent", classifier_agent)
    graph.add_node("router_agent", router_agent)
    graph.add_node("tool_agent", tool_agent)
    graph.add_node("knowledge_agent", knowledge_agent)
    graph.add_node("resolver_agent", resolver_agent)
    graph.add_node("escalation_agent", escalation_agent)
    graph.add_node("memory_agent", memory_agent)
    graph.add_node("response_agent", response_agent)

    graph.add_edge(START, "intake_agent")
    graph.add_edge("intake_agent", "classifier_agent")
    graph.add_edge("classifier_agent", "router_agent")

    graph.add_conditional_edges(
        "router_agent",
        _route_after_router,
        {
            "tool_agent": "tool_agent",
            "knowledge_agent": "knowledge_agent",
        },
    )
    graph.add_edge("tool_agent", "knowledge_agent")

    graph.add_conditional_edges(
        "knowledge_agent",
        _route_after_knowledge,
        {
            "resolver_agent": "resolver_agent",
            "escalation_agent": "escalation_agent",
        },
    )
    graph.add_edge("resolver_agent", "memory_agent")
    graph.add_edge("escalation_agent", "memory_agent")
    graph.add_edge("memory_agent", "response_agent")
    graph.add_edge("response_agent", END)

    return graph.compile(checkpointer=MemorySaver())


orchestrator = build_workflow()
