import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig

from solution.agentic.logging_utils import append_log
from solution.agentic.state import TicketState
from solution.agentic.tools.knowledge_tools import KnowledgeTools
from solution.agentic.tools.memory_tools import MemoryTools
from solution.agentic.tools.support_tools import SupportTools
from solution.data.models import udahub
from solution.db import CORE_DB_PATH, session_scope, sqlite_engine

support_tools = SupportTools()
knowledge_tools = KnowledgeTools()
memory_tools = MemoryTools()
core_engine = sqlite_engine(CORE_DB_PATH)


def _thread_id(config: RunnableConfig | None) -> str:
    if not config:
        return "default-thread"
    return str(config.get("configurable", {}).get("thread_id", "default-thread"))


def _decision_entry(node: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"node": node, "details": details}


def _extract_preferences(message: str) -> dict[str, Any]:
    lowered = message.lower()
    preferences: dict[str, Any] = {}
    if "email" in lowered and "notification" in lowered:
        preferences["notification_channel"] = "email"
    if "push" in lowered and "notification" in lowered:
        preferences["notification_channel"] = "push"
    if "weekend" in lowered:
        preferences["preferred_booking_time"] = "weekend"
    return preferences


def intake_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    ticket_id = state.get("ticket_id") or str(uuid.uuid4())
    account_id = state.get("account_id", "cultpass")
    external_user_id = state.get("external_user_id", "")
    ticket_text = (state.get("ticket_text") or "").strip()

    history = list(state.get("conversation_history", []))
    if ticket_text:
        history.append(ticket_text)

    long_term_context = {}
    if external_user_id:
        long_term_context = memory_tools.load_user_context(account_id, external_user_id)

    append_log(
        thread_id=thread_id,
        ticket_id=ticket_id,
        node="intake_agent",
        event="ticket_ingested",
        details={"account_id": account_id, "external_user_id": external_user_id, "message_length": len(ticket_text)},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(
        _decision_entry("intake_agent", {"loaded_long_term_context": bool(long_term_context), "history_size": len(history)})
    )

    return {
        "ticket_id": ticket_id,
        "account_id": account_id,
        "external_user_id": external_user_id,
        "ticket_text": ticket_text,
        "metadata": state.get("metadata", {}),
        "conversation_history": history,
        "long_term_context": long_term_context,
        "decision_log": decision_log,
    }


def classifier_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    text = state.get("ticket_text", "").lower()
    metadata = state.get("metadata", {})

    category = "general"
    if any(word in text for word in ("login", "password", "access")):
        category = "login"
    elif any(word in text for word in ("refund", "charge", "billing", "payment")):
        category = "billing"
    elif any(word in text for word in ("subscription", "pause", "cancel", "quota")):
        category = "subscription"
    elif any(word in text for word in ("reservation", "book", "event", "qr")):
        category = "reservation"
    elif any(word in text for word in ("crash", "bug", "error", "app")):
        category = "technical"
    elif any(word in text for word in ("blocked", "account")):
        category = "account"

    urgency = str(metadata.get("urgency", "normal")).lower()
    if any(word in text for word in ("urgent", "immediately", "asap")):
        urgency = "high"

    complexity = "low"
    if len(text.split()) > 30 or "multiple" in text or "still" in text:
        complexity = "medium"
    if any(word in text for word in ("escalate", "legal", "compliance")):
        complexity = "high"

    classification = {
        "category": category,
        "urgency": urgency,
        "complexity": complexity,
    }

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="classifier_agent",
        event="ticket_classified",
        details=classification,
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("classifier_agent", classification))

    return {"classification": classification, "decision_log": decision_log}


def router_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    category = state["classification"]["category"]

    route = "knowledge_agent"
    reason = "knowledge_first"
    if category in {"billing", "subscription", "reservation", "account"}:
        route = "tool_agent"
        reason = "requires_db_lookup"

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="router_agent",
        event="route_selected",
        details={"route": route, "reason": reason, "category": category},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("router_agent", {"route": route, "reason": reason}))
    return {"route": route, "routed_reason": reason, "decision_log": decision_log}


def tool_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    category = state["classification"]["category"]
    external_user_id = state.get("external_user_id", "")
    ticket_text = state.get("ticket_text", "").lower()

    outputs: list[dict[str, Any]] = []
    outputs.append({"tool": "account_lookup", "result": support_tools.account_lookup(external_user_id)})

    if category == "reservation":
        outputs.append({"tool": "get_recent_reservations", "result": support_tools.get_recent_reservations(external_user_id)})

    if category == "subscription" and "pause" in ticket_text:
        outputs.append(
            {
                "tool": "set_subscription_status",
                "result": support_tools.set_subscription_status(external_user_id, "paused"),
            }
        )

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="tool_agent",
        event="tools_executed",
        details={"tool_count": len(outputs), "tools": [item["tool"] for item in outputs]},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(
        _decision_entry("tool_agent", {"tool_count": len(outputs), "tools": [item["tool"] for item in outputs]})
    )

    return {"tool_outputs": outputs, "decision_log": decision_log}


def knowledge_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    result = knowledge_tools.retrieve(state["account_id"], state.get("ticket_text", ""), top_k=3)
    articles = result["articles"]
    confidence = float(result["confidence"])

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="knowledge_agent",
        event="knowledge_retrieved",
        details={"article_count": len(articles), "confidence": confidence},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("knowledge_agent", {"article_count": len(articles), "confidence": confidence}))

    return {"retrieved_articles": articles, "confidence": confidence, "decision_log": decision_log}


def resolver_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    articles = state.get("retrieved_articles", [])
    top_article = articles[0]

    tool_lines: list[str] = []
    for output in state.get("tool_outputs", []):
        tool_name = output["tool"]
        tool_result = output["result"]
        if tool_result.get("ok"):
            tool_lines.append(f"- Tool `{tool_name}` succeeded.")
        else:
            tool_lines.append(f"- Tool `{tool_name}` returned `{tool_result.get('error')}`.")

    prior_note = ""
    resolved_before = int(state.get("long_term_context", {}).get("resolved_count", 0))
    if resolved_before > 0:
        prior_note = f"I can see we have already resolved {resolved_before} issue(s) together, so I will keep this concise.\n\n"

    response = (
        f"{prior_note}Here is the best match from our knowledge base: **{top_article['title']}**.\n\n"
        f"{top_article['content']}\n\n"
        "Action summary:\n"
        + ("\n".join(tool_lines) if tool_lines else "- No account-level action was required for this request.")
    )

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="resolver_agent",
        event="ticket_resolved",
        details={"article_id": top_article["article_id"], "confidence": state.get("confidence", 0.0)},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("resolver_agent", {"status": "resolved", "article": top_article["title"]}))

    return {
        "response": response,
        "escalate": False,
        "escalation_reason": "",
        "decision_log": decision_log,
    }


def escalation_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    category = state.get("classification", {}).get("category", "general")
    reason = (
        "No sufficiently relevant knowledge article was found"
        if not state.get("retrieved_articles")
        else f"Top confidence {state.get('confidence', 0.0)} is below threshold"
    )

    response = (
        "I am escalating this ticket to a human specialist so we can resolve it correctly.\n\n"
        f"Escalation reason: {reason}.\n"
        f"Detected issue category: {category}.\n"
        "A support lead will review your case with full context shortly."
    )

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="escalation_agent",
        event="ticket_escalated",
        details={"reason": reason, "category": category, "confidence": state.get("confidence", 0.0)},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("escalation_agent", {"status": "escalated", "reason": reason}))

    return {
        "response": response,
        "escalate": True,
        "escalation_reason": reason,
        "decision_log": decision_log,
    }


def memory_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)

    preferences_update = _extract_preferences(state.get("ticket_text", ""))
    status = "escalated" if state.get("escalate") else "resolved"
    issue_type = state.get("classification", {}).get("category", "general")

    with session_scope(core_engine) as session:
        account = (
            session.query(udahub.Account)
            .filter(udahub.Account.account_id == state["account_id"])
            .one_or_none()
        )
        if not account:
            account = udahub.Account(account_id=state["account_id"], account_name="CultPass Card")
            session.add(account)
            session.flush()

        user = (
            session.query(udahub.User)
            .filter(
                udahub.User.account_id == state["account_id"],
                udahub.User.external_user_id == state["external_user_id"],
            )
            .one_or_none()
        )
        if not user:
            user = udahub.User(
                user_id=str(uuid.uuid4()),
                account_id=state["account_id"],
                external_user_id=state["external_user_id"],
                user_name=f"user-{state['external_user_id']}",
            )
            session.add(user)
            session.flush()

        ticket = (
            session.query(udahub.Ticket)
            .filter(udahub.Ticket.ticket_id == state["ticket_id"])
            .one_or_none()
        )
        if not ticket:
            ticket = udahub.Ticket(
                ticket_id=state["ticket_id"],
                account_id=state["account_id"],
                user_id=user.user_id,
                channel=str(state.get("metadata", {}).get("channel", "chat")),
            )
            session.add(ticket)
            session.flush()

        metadata = (
            session.query(udahub.TicketMetadata)
            .filter(udahub.TicketMetadata.ticket_id == ticket.ticket_id)
            .one_or_none()
        )
        if metadata:
            metadata.status = status
            metadata.main_issue_type = issue_type
            metadata.tags = str(state.get("metadata", {}).get("tags", issue_type))
            metadata.urgency = state.get("classification", {}).get("urgency", "normal")
            metadata.complexity = state.get("classification", {}).get("complexity", "low")
        else:
            session.add(
                udahub.TicketMetadata(
                    ticket_id=ticket.ticket_id,
                    status=status,
                    main_issue_type=issue_type,
                    tags=str(state.get("metadata", {}).get("tags", issue_type)),
                    urgency=state.get("classification", {}).get("urgency", "normal"),
                    complexity=state.get("classification", {}).get("complexity", "low"),
                )
            )
        session.add(
            udahub.TicketMessage(
                message_id=str(uuid.uuid4()),
                ticket_id=ticket.ticket_id,
                role=udahub.RoleEnum.user,
                content=state.get("ticket_text", ""),
            )
        )
        session.add(
            udahub.TicketMessage(
                message_id=str(uuid.uuid4()),
                ticket_id=ticket.ticket_id,
                role=udahub.RoleEnum.ai,
                content=state.get("response", ""),
            )
        )

    memory_tools.persist_interaction(
        account_id=state["account_id"],
        external_user_id=state["external_user_id"],
        ticket_id=state["ticket_id"],
        user_message=state.get("ticket_text", ""),
        final_response=state.get("response", ""),
        status=status,
        issue_type=issue_type,
        preferences_update=preferences_update,
    )

    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="memory_agent",
        event="memory_persisted",
        details={"status": status, "preferences_updated": bool(preferences_update)},
    )

    decision_log = list(state.get("decision_log", []))
    decision_log.append(_decision_entry("memory_agent", {"status": status}))
    return {"decision_log": decision_log}


def response_agent(state: TicketState, config: RunnableConfig | None = None) -> TicketState:
    thread_id = _thread_id(config)
    append_log(
        thread_id=thread_id,
        ticket_id=state["ticket_id"],
        node="response_agent",
        event="response_ready",
        details={"escalated": state.get("escalate", False)},
    )
    return {"response": state.get("response", "")}
