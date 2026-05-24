from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from solution.db import DATA_ROOT

LOG_PATH = DATA_ROOT / "core" / "workflow_logs.jsonl"


def append_log(thread_id: str, ticket_id: str, node: str, event: str, details: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "thread_id": thread_id,
        "ticket_id": ticket_id,
        "node": node,
        "event": event,
        "details": details,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
