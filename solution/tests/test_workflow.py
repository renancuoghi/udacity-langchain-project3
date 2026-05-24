from __future__ import annotations

import json
import uuid
import unittest
from pathlib import Path

from sqlalchemy import func

from solution.agentic.logging_utils import LOG_PATH
from solution.agentic.workflow import orchestrator
from solution.data.models import cultpass, udahub
from solution.db import CORE_DB_PATH, EXTERNAL_DB_PATH, session_scope, sqlite_engine
from solution.setup_databases import setup_all


class WorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setup_all()
        if LOG_PATH.exists():
            LOG_PATH.unlink()

    def _invoke(self, text: str, external_user_id: str = "a4ab87", metadata: dict | None = None):
        ticket_id = str(uuid.uuid4())
        thread_id = f"thread-{uuid.uuid4()}"
        payload = {
            "ticket_id": ticket_id,
            "account_id": "cultpass",
            "external_user_id": external_user_id,
            "ticket_text": text,
            "metadata": metadata or {"channel": "chat", "urgency": "normal"},
        }
        result = orchestrator.invoke(payload, config={"configurable": {"thread_id": thread_id}})
        return result, ticket_id

    def test_database_setup_contains_minimum_articles(self) -> None:
        core_engine = sqlite_engine(CORE_DB_PATH)
        with session_scope(core_engine) as session:
            article_count = session.query(func.count(udahub.Knowledge.article_id)).scalar() or 0

        self.assertGreaterEqual(article_count, 14)

    def test_successful_resolution_uses_knowledge(self) -> None:
        result, _ = self._invoke("I forgot my password and cannot login to my account")
        self.assertFalse(result.get("escalate", True))
        self.assertIn("knowledge base", result.get("response", "").lower())
        self.assertGreaterEqual(float(result.get("confidence", 0.0)), 0.25)

    def test_unknown_issue_escalates(self) -> None:
        result, _ = self._invoke("Our legal hold export API checksum does not match your retention policy")
        self.assertTrue(result.get("escalate", False))
        self.assertIn("escalating", result.get("response", "").lower())

    def test_subscription_pause_calls_tool_and_updates_external_db(self) -> None:
        user_id = "f556c0"
        result, _ = self._invoke("Please pause my subscription for now", external_user_id=user_id)

        tools = [entry["tool"] for entry in result.get("tool_outputs", [])]
        self.assertIn("set_subscription_status", tools)

        external_engine = sqlite_engine(EXTERNAL_DB_PATH)
        with session_scope(external_engine) as session:
            subscription = session.query(cultpass.Subscription).filter(cultpass.Subscription.user_id == user_id).one()
            status = subscription.status

        self.assertEqual(status, "paused")

    def test_long_term_memory_retrieval_across_sessions(self) -> None:
        user_id = "88382b"

        first, _ = self._invoke(
            "I cannot login and I prefer email notifications",
            external_user_id=user_id,
        )
        self.assertFalse(first.get("escalate", True))

        second, _ = self._invoke(
            "I still cannot login today",
            external_user_id=user_id,
        )

        context = second.get("long_term_context", {})
        self.assertGreaterEqual(int(context.get("resolved_count", 0)), 1)
        self.assertIn("recent_interactions", context)

    def test_structured_logs_are_written(self) -> None:
        self._invoke("How do I reserve an event?")
        self.assertTrue(LOG_PATH.exists())

        with LOG_PATH.open("r", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]

        self.assertGreater(len(lines), 0)
        self.assertTrue(any(item.get("node") == "router_agent" for item in lines))


if __name__ == "__main__":
    unittest.main()
