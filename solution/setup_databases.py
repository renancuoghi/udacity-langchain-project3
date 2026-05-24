from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solution.data.models import cultpass, udahub
from solution.db import CORE_DB_PATH, EXTERNAL_DB_PATH, reset_sqlite, session_scope, sqlite_engine

ACCOUNT_ID = "cultpass"
ACCOUNT_NAME = "CultPass Card"


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def setup_external_db() -> Path:
    reset_sqlite(EXTERNAL_DB_PATH)
    engine = sqlite_engine(EXTERNAL_DB_PATH)
    cultpass.Base.metadata.create_all(bind=engine)

    users_path = Path(__file__).resolve().parent / "data" / "external" / "cultpass_users.jsonl"
    experiences_path = Path(__file__).resolve().parent / "data" / "external" / "cultpass_experiences.jsonl"

    users = _read_jsonl(users_path)
    experiences = _read_jsonl(experiences_path)

    now = datetime.now(tz=timezone.utc)

    with session_scope(engine) as session:
        for user in users:
            session.add(
                cultpass.User(
                    user_id=user["id"],
                    full_name=user["name"],
                    email=user["email"],
                    is_blocked=bool(user["is_blocked"]),
                )
            )
            session.add(
                cultpass.Subscription(
                    subscription_id=str(uuid.uuid4()),
                    user_id=user["id"],
                    status="active" if not user["is_blocked"] else "suspended",
                    tier="premium" if user["id"].endswith(("d", "f")) else "standard",
                    monthly_quota=6 if user["id"].endswith(("d", "f")) else 4,
                    started_at=now - timedelta(days=40),
                )
            )

        for idx, exp in enumerate(experiences):
            session.add(
                cultpass.Experience(
                    experience_id=str(uuid.uuid4()),
                    title=exp["title"],
                    description=exp["description"],
                    location=exp["location"],
                    when=now + timedelta(days=idx + 1),
                    slots_available=max(2, 30 - idx),
                    is_premium=(idx % 3 == 0),
                )
            )

        first_user = users[0]["id"]
        db_experiences = session.query(cultpass.Experience).limit(2).all()
        for exp in db_experiences:
            session.add(
                cultpass.Reservation(
                    reservation_id=str(uuid.uuid4()),
                    user_id=first_user,
                    experience_id=exp.experience_id,
                    status="confirmed",
                )
            )

    return EXTERNAL_DB_PATH


def setup_core_db() -> Path:
    reset_sqlite(CORE_DB_PATH)
    engine = sqlite_engine(CORE_DB_PATH)
    udahub.Base.metadata.create_all(bind=engine)

    users_path = Path(__file__).resolve().parent / "data" / "external" / "cultpass_users.jsonl"
    articles_path = Path(__file__).resolve().parent / "data" / "external" / "cultpass_articles.jsonl"

    users = _read_jsonl(users_path)
    articles = _read_jsonl(articles_path)

    with session_scope(engine) as session:
        session.add(udahub.Account(account_id=ACCOUNT_ID, account_name=ACCOUNT_NAME))

        for article in articles:
            session.add(
                udahub.Knowledge(
                    article_id=str(uuid.uuid4()),
                    account_id=ACCOUNT_ID,
                    title=article["title"],
                    content=article["content"],
                    tags=article["tags"],
                )
            )

        user = users[0]
        app_user = udahub.User(
            user_id=str(uuid.uuid4()),
            account_id=ACCOUNT_ID,
            external_user_id=user["id"],
            user_name=user["name"],
        )
        session.add(app_user)

        ticket_id = str(uuid.uuid4())
        session.add(
            udahub.Ticket(
                ticket_id=ticket_id,
                account_id=ACCOUNT_ID,
                user_id=app_user.user_id,
                channel="chat",
            )
        )
        session.add(
            udahub.TicketMetadata(
                ticket_id=ticket_id,
                status="open",
                main_issue_type="login",
                tags="login,password",
                urgency="normal",
                complexity="low",
            )
        )
        session.add(
            udahub.TicketMessage(
                message_id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                role=udahub.RoleEnum.user,
                content="I cannot log in to my account. Please help.",
            )
        )

    return CORE_DB_PATH


def setup_all() -> tuple[Path, Path]:
    external = setup_external_db()
    core = setup_core_db()
    return external, core


if __name__ == "__main__":
    ext_path, core_path = setup_all()
    print(f"External DB ready: {ext_path}")
    print(f"Core DB ready: {core_path}")
