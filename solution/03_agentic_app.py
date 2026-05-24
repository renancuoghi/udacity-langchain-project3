from __future__ import annotations

from solution.agentic.workflow import orchestrator
from solution.setup_databases import setup_all
from solution.utils import chat_interface


def main() -> None:
    setup_all()
    chat_interface(orchestrator)


if __name__ == "__main__":
    main()
