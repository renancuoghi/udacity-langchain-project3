from __future__ import annotations

from typing import Any, TypedDict


class TicketState(TypedDict, total=False):
    ticket_id: str
    account_id: str
    external_user_id: str
    ticket_text: str
    metadata: dict[str, Any]
    conversation_history: list[str]
    long_term_context: dict[str, Any]
    classification: dict[str, Any]
    route: str
    routed_reason: str
    tool_outputs: list[dict[str, Any]]
    retrieved_articles: list[dict[str, Any]]
    confidence: float
    escalate: bool
    escalation_reason: str
    response: str
    decision_log: list[dict[str, Any]]
