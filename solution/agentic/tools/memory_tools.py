from __future__ import annotations

import json
import uuid
from typing import Any

from solution.data.models import udahub
from solution.db import CORE_DB_PATH, session_scope, sqlite_engine


class MemoryTools:
    def __init__(self) -> None:
        self.core_engine = sqlite_engine(CORE_DB_PATH)

    def load_user_context(self, account_id: str, external_user_id: str) -> dict[str, Any]:
        with session_scope(self.core_engine) as session:
            memory = (
                session.query(udahub.LongTermMemory)
                .filter(
                    udahub.LongTermMemory.account_id == account_id,
                    udahub.LongTermMemory.external_user_id == external_user_id,
                )
                .one_or_none()
            )
            interactions = (
                session.query(udahub.InteractionHistory)
                .filter(
                    udahub.InteractionHistory.account_id == account_id,
                    udahub.InteractionHistory.external_user_id == external_user_id,
                )
                .order_by(udahub.InteractionHistory.created_at.desc())
                .limit(3)
                .all()
            )

        if not memory:
            return {
                "preferences": {},
                "recent_issues": [],
                "last_resolution": "",
                "resolved_count": 0,
                "recent_interactions": [
                    {"ticket_id": row.ticket_id, "status": row.status, "final_response": row.final_response}
                    for row in interactions
                ],
            }

        return {
            "preferences": json.loads(memory.preferences or "{}"),
            "recent_issues": json.loads(memory.recent_issues or "[]"),
            "last_resolution": memory.last_resolution,
            "resolved_count": memory.resolved_count,
            "recent_interactions": [
                {"ticket_id": row.ticket_id, "status": row.status, "final_response": row.final_response}
                for row in interactions
            ],
        }

    def persist_interaction(
        self,
        account_id: str,
        external_user_id: str,
        ticket_id: str,
        user_message: str,
        final_response: str,
        status: str,
        issue_type: str,
        preferences_update: dict[str, Any],
    ) -> None:
        with session_scope(self.core_engine) as session:
            memory = (
                session.query(udahub.LongTermMemory)
                .filter(
                    udahub.LongTermMemory.account_id == account_id,
                    udahub.LongTermMemory.external_user_id == external_user_id,
                )
                .one_or_none()
            )
            if not memory:
                memory = udahub.LongTermMemory(
                    memory_id=str(uuid.uuid4()),
                    account_id=account_id,
                    external_user_id=external_user_id,
                    preferences="{}",
                    recent_issues="[]",
                )
                session.add(memory)
                session.flush()

            preferences = json.loads(memory.preferences or "{}")
            preferences.update(preferences_update)

            recent_issues = json.loads(memory.recent_issues or "[]")
            if issue_type:
                recent_issues.append(issue_type)
                recent_issues = recent_issues[-5:]

            memory.preferences = json.dumps(preferences, ensure_ascii=True)
            memory.recent_issues = json.dumps(recent_issues, ensure_ascii=True)
            memory.last_resolution = final_response
            if status == "resolved":
                memory.resolved_count = int(memory.resolved_count or 0) + 1

            session.add(
                udahub.InteractionHistory(
                    interaction_id=str(uuid.uuid4()),
                    ticket_id=ticket_id,
                    account_id=account_id,
                    external_user_id=external_user_id,
                    user_message=user_message,
                    final_response=final_response,
                    status=status,
                )
            )
