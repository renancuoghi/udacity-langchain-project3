# UDA-Hub LangGraph Project (Solution)

This solution implements a LangGraph-based multi-agent customer support system for the CultPass account inside UDA-Hub.

## What Is Included
- Multi-agent orchestration using LangGraph with 9 specialized nodes.
- Intelligent routing based on ticket classification and metadata.
- Knowledge retrieval over an expanded support KB (14 articles).
- Escalation path when confidence is low or no article matches.
- Support tools abstracting CultPass database operations.
- Persistent memory (interaction history + long-term preferences).
- Structured JSONL logging for agent decisions and tool outcomes.
- Automated tests for setup, routing, retrieval, escalation, tool usage, and memory.

## Project Structure
- `solution/agentic/workflow.py`: LangGraph definition and orchestration.
- `solution/agentic/agents/nodes.py`: specialized agent node implementations.
- `solution/agentic/tools/`: knowledge, support, and memory tools.
- `solution/agentic/design/architecture.md`: architecture design and diagram.
- `solution/setup_databases.py`: reproducible DB setup for core and external DBs.
- `solution/03_agentic_app.py`: runnable app entry point.
- `solution/tests/test_workflow.py`: end-to-end integration tests.

## Requirements
- Python `3.14.4`
- Main libraries used:
  - `langgraph==1.2.0`
  - `langchain==1.3.1`
  - `langchain-openai==1.2.1`
  - `langgraph-supervisor==0.0.31`
  - `sqlalchemy==2.0.49`

## Run the App
From project root:

```bash
./.venv/bin/python solution/03_agentic_app.py
```

This command:
1. Recreates both SQLite DBs in `solution/data/`
2. Starts an interactive chat interface

## Run Tests
From project root:

```bash
./.venv/bin/python -m unittest discover -s solution/tests -p "test_*.py" -v
```

## Design Highlights
- Architecture pattern: supervisor-style orchestrated graph.
- At least 4 specialized agents (implemented with 9 nodes).
- Session memory through `thread_id` and graph checkpointing.
- Long-term memory persisted in `long_term_memory` and `interaction_history` tables.
- Database abstraction tools for support operations.

## Notes
- All implementation artifacts are contained inside `solution/`.
- No imports reference directories outside `solution/`.
- Databases are generated locally at runtime and are not required in submission.
