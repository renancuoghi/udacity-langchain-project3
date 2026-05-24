from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph.state import CompiledStateGraph


def chat_interface(agent: CompiledStateGraph, account_id: str = "cultpass", external_user_id: str = "a4ab87") -> None:
    session_ticket = str(uuid.uuid4())
    print(f"Starting support session. Ticket ID: {session_ticket}")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Assistant: Goodbye!")
            break

        state: dict[str, Any] = {
            "ticket_id": session_ticket,
            "account_id": account_id,
            "external_user_id": external_user_id,
            "ticket_text": user_input,
            "metadata": {"channel": "chat", "urgency": "normal"},
        }
        config = {"configurable": {"thread_id": f"thread-{session_ticket}"}}
        result = agent.invoke(state, config=config)
        print("Assistant:", result.get("response", "I could not produce a response."))
        print()
