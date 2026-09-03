"""
planner/db.py — the ONLY file that knows SQLite exists.
Why a generator here: step 5 plugs this straight into FastAPI Depends().
"""
from sqlmodel import Session, SQLModel, create_engine

from planner import models  # noqa: F401  — imports register all tables

DB_FILE = "planner.db"

# check_same_thread=False: FastAPI's threadpool touches this engine in step 5.
# PITFALL pre-empted: without this, the API 500s on the first parallel request.
engine = create_engine(
    f"sqlite:///{DB_FILE}",
    connect_args={"check_same_thread": False},
)


def create_all() -> None:
    # DEV RESET POLICY: we have no Alembic, on purpose. Schema changes
    # during the 3-day build = delete planner.db and re-seed. Flagged so
    # nobody wastes 20 minutes debugging a stale table.
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
