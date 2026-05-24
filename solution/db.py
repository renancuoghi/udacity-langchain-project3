from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

SOLUTION_ROOT = Path(__file__).resolve().parent
DATA_ROOT = SOLUTION_ROOT / "data"
CORE_DB_PATH = DATA_ROOT / "core" / "udahub.db"
EXTERNAL_DB_PATH = DATA_ROOT / "external" / "cultpass.db"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sqlite_engine(db_path: Path, echo: bool = False) -> Engine:
    ensure_parent_dir(db_path)
    return create_engine(
        f"sqlite:///{db_path}",
        echo=echo,
        future=True,
        poolclass=NullPool,
    )


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    session = session_local()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_sqlite(db_path: Path) -> None:
    ensure_parent_dir(db_path)
    if db_path.exists():
        db_path.unlink()
