'''
Low-level database engine and inspection helpers
'''

import os 
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text 
from sqlalchemy.engine import Engine

# Load .env once at import time 
load_dotenv()

DB_URI = os.getenv("DB_URI")

SQL_DIALECT = os.getenv("SQL_DIALECT" or detect_dialect(DB_URI or ""))

_raw_tables = os.getenv("SCHEMA_TABLES", "").strip()
SCHEMA_TABLES = [t.strip() for t in _raw_tables.split(",") if t.strip()] or None

# SQLAlchemy engine 
_engine: Engine | None = None 

def get_engine() -> Engine: 
    '''Return a cached SQLAlchemy engine for DB_URI'''
    global _engine
    if _engine is None:
        if not DB_URI:
            raise RuntimeError(
                'DB_`URI is not set. Copy .env.example to .env and set'
            )
        _engine = create_engine(DB_URI, future = True)
    return _engine

def test_connection() -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def list_tables() -> list[str]:
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if SCHEMA_TABLES:
        tables = [t for t in tables if t in SCHEMA_TABLES]
    return tables

def get_column_info(table: str) -> list[dict[str, Any]]:
    engine = get_engine()
    inspector = inspect(engine)
    raw_cols = inspector.get_columns(table)

    normalized = []
    for col in raw_cols:
        normalized.append(
            {
                "name": col.get("name"),
                "type": str(col.get("type", "")),
                "nullable": col.get("nullable", True),
                "default": col.get("default"),
                "primary_key": col.get("primary_key", False),
            }
        )
    return normalized

def get_foreign_keys(table: str) -> list[dict[str, Any]]:
    engine = get_engine()
    inspector = inspect(engine)
    try:
        return inspector.get_foreign_keys(table)
    except Exception:
        return []
       