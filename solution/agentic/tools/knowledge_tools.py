from __future__ import annotations

import re
from typing import Any

from solution.data.models import udahub
from solution.db import CORE_DB_PATH, session_scope, sqlite_engine

WORD_PATTERN = re.compile(r"[a-zA-Z0-9']+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in WORD_PATTERN.findall(text) if len(t) > 2}


class KnowledgeTools:
    def __init__(self) -> None:
        self.core_engine = sqlite_engine(CORE_DB_PATH)

    def retrieve(self, account_id: str, query: str, top_k: int = 3) -> dict[str, Any]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return {"ok": True, "articles": [], "confidence": 0.0}

        with session_scope(self.core_engine) as session:
            rows = (
                session.query(udahub.Knowledge)
                .filter(udahub.Knowledge.account_id == account_id)
                .all()
            )

        scored: list[tuple[float, udahub.Knowledge]] = []
        for row in rows:
            article_tokens = _tokens(row.title + " " + row.content + " " + (row.tags or ""))
            overlap = len(query_tokens & article_tokens)
            if overlap == 0:
                continue

            coverage = overlap / max(1, len(query_tokens))
            tag_boost = 0.08 if row.tags and any(t in row.tags.lower() for t in query_tokens) else 0.0
            score = min(1.0, coverage + tag_boost)
            scored.append((score, row))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top_scored = scored[:top_k]

        articles = [
            {
                "article_id": row.article_id,
                "title": row.title,
                "content": row.content,
                "tags": row.tags,
                "score": round(score, 3),
            }
            for score, row in top_scored
        ]
        confidence = top_scored[0][0] if top_scored else 0.0
        return {"ok": True, "articles": articles, "confidence": round(confidence, 3)}
