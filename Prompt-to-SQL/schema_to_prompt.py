"""
schema_to_prompt.py — Build a prompt-ready schema description for an LLM
from ANY database, including type-mapping hints and query rules.

Supported: SQLite, PostgreSQL, MySQL/MariaDB, SQL Server, Oracle (via SQLAlchemy)

Install:
    pip install sqlalchemy
    pip install psycopg2-binary   # PostgreSQL
    pip install pymysql           # MySQL/MariaDB
    pip install pyodbc            # SQL Server
    pip install oracledb          # Oracle
"""

import argparse
import json
import re
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.types import (
    Integer, BigInteger, SmallInteger, Float, Numeric, DECIMAL,
    String, Text, Unicode, UnicodeText, Boolean, Date, DateTime, Time,
    TIMESTAMP, LargeBinary, JSON, Interval,
)


# ============================================================
# 1. Type classification
# ============================================================

# SQLAlchemy type class -> semantic category
_TYPE_CATEGORY = {
    Integer: "integer", BigInteger: "integer", SmallInteger: "integer",
    Float: "float", Numeric: "decimal", DECIMAL: "decimal",
    String: "string", Text: "string", Unicode: "string",
    UnicodeText: "string",
    Boolean: "boolean",
    Date: "date", DateTime: "datetime", Time: "time", TIMESTAMP: "datetime",
    LargeBinary: "binary",
    JSON: "json",
    Interval: "interval",
}


def classify_type(col_type) -> str:
    """Return semantic category for a SQLAlchemy column type."""
    for cls, cat in _TYPE_CATEGORY.items():
        if isinstance(col_type, cls):
            return cat
    return "other"


# Regex hints for names that imply a role regardless of type
_DATETIME_NAME_RE = re.compile(
    r"(date|time|timestamp|_at$|_dt$|created|updated|modified|"
    r"purchase|approved|delivered|shipping|review_)",
    re.IGNORECASE,
)
_MONEY_NAME_RE = re.compile(
    r"(price|amount|cost|value|total|subtotal|payment|fee|"
    r"freight|shipping|tax|discount|revenue|salary|balance)",
    re.IGNORECASE,
)
_ID_NAME_RE = re.compile(r"(^id$|_id$|_key$|_code$|_no$|_number$)", re.IGNORECASE)
_LAT_NAME_RE = re.compile(r"(lat|latitude)", re.IGNORECASE)
_LNG_NAME_RE = re.compile(r"(lng|lon|longitude)", re.IGNORECASE)


def infer_role(table: str, col_name: str, category: str) -> str | None:
    """Assign a semantic role based on type + name heuristics."""
    name = col_name.lower()

    # Type takes priority when unambiguous
    if category in ("date", "datetime", "time"):
        return f"{category}"
    if category == "decimal":
        return "decimal (use ROUND for aggregates)"
    if category == "boolean":
        return "boolean (0/1 or TRUE/FALSE)"

    # Name-based inference
    if _LAT_NAME_RE.search(name):
        return "coordinate (latitude)"
    if _LNG_NAME_RE.search(name):
        return "coordinate (longitude)"
    if _MONEY_NAME_RE.search(name) and category in ("float", "integer"):
        return "money (round to 2 decimals)"
    if _DATETIME_NAME_RE.search(name) and category == "string":
        return "datetime stored as TEXT"
    if _ID_NAME_RE.search(name):
        return "identifier"
    return None


# ============================================================
# 2. Schema reading (DB-agnostic via SQLAlchemy)
# ============================================================

def read_schema(url: str, include_system: bool = False) -> dict:
    """Read tables, columns, PKs, and FKs from any DB."""
    engine = create_engine(url)
    insp = inspect(engine)
    dialect = engine.dialect.name

    schema_name = None
    if dialect in ("postgresql", "mssql", "oracle"):
        schema_name = insp.default_schema_name

    tables = insp.get_table_names(schema=schema_name)
    if not include_system:
        tables = [t for t in tables
                  if not t.startswith(("sqlite_", "pg_", "sys", "information_schema"))]

    schema = {}
    for t in sorted(tables):
        # PK
        try:
            pk = insp.get_pk_constraint(t, schema=schema_name) or {}
            pk_cols = set(pk.get("constrained_columns") or [])
        except Exception:
            pk_cols = set()

        # Unique
        uniques = set()
        try:
            for uc in insp.get_unique_constraints(t, schema=schema_name):
                for c in uc.get("column_names") or []:
                    uniques.add(c)
        except Exception:
            pass
        try:
            for idx in insp.get_indexes(t, schema=schema_name):
                if idx.get("unique"):
                    for c in idx.get("column_names") or []:
                        uniques.add(c)
        except Exception:
            pass

        # Columns
        cols = []
        for c in insp.get_columns(t, schema=schema_name):
            category = classify_type(c["type"])
            cols.append({
                "name": c["name"],
                "type": str(c["type"]),
                "category": category,
                "not_null": not c.get("nullable", True),
                "default": c.get("default"),
                "pk": c["name"] in pk_cols,
                "unique": c["name"] in uniques,
                "autoincrement": bool(c.get("autoincrement")),
            })

        # FKs
        fks = []
        try:
            for fk in insp.get_foreign_keys(t, schema=schema_name):
                opts = fk.get("options", {}) or {}
                fks.append({
                    "columns": fk["constrained_columns"],
                    "ref_table": fk["referred_table"],
                    "ref_columns": fk["referred_columns"],
                    "on_update": opts.get("onupdate"),
                    "on_delete": opts.get("ondelete"),
                })
        except Exception:
            pass

        schema[t] = {
            "columns": cols,
            "declared_fks": fks,
        }

    engine.dispose()
    return schema


# ============================================================
# 3. Relation inference (for DBs with no declared FKs)
# ============================================================

def infer_relations(schema: dict) -> list[tuple]:
    """
    Infer FK-like relations by naming.
    Rule: if table A has column '<x>_id' and table B has a matching column
    named 'id', '<x>_id', or B is named like <x> (plural/singular).
    """
    # Build a column index: column_name -> [(table, column), ...]
    col_index = {}
    for t, info in schema.items():
        for c in info["columns"]:
            col_index.setdefault(c["name"].lower(), []).append((t, c["name"]))

    relations = set()

    for t, info in schema.items():
        for c in info["columns"]:
            name = c["name"]
            m = re.match(r"^(.+?)_(?:id|key|code|no|number)$", name, re.IGNORECASE)
            if not m:
                continue
            base = m.group(1).lower()

            # Candidate 1: table named like base (singular/plural variants)
            for cand in (base, base + "s", base + "es", base + "ies"):
                if cand in schema and cand != t:
                    # Prefer 'id' column
                    cand_cols = [cc["name"] for cc in schema[cand]["columns"]]
                    ref_col = "id" if "id" in cand_cols else cand_cols[0]
                    relations.add((t, name, cand, ref_col))

            # Candidate 2: any table with a column named the same
            for t2, c2 in col_index.get(name.lower(), []):
                if t2 != t:
                    relations.add((t, name, t2, c2))

    # Deduplicate and prefer declared-shaped pairs
    return sorted(relations)


def merge_relations(schema: dict) -> list[dict]:
    """Return declared FKs if any exist, else inferred, per table."""
    declared = []
    for t, info in schema.items():
        for fk in info["declared_fks"]:
            for lc, rc in zip(fk["columns"], fk["ref_columns"]):
                declared.append({
                    "from": f"{t}.{lc}",
                    "to": f"{fk['ref_table']}.{rc}",
                    "declared": True,
                })

    if declared:
        return declared

    inferred = []
    for t, c, rt, rc in infer_relations(schema):
        inferred.append({
            "from": f"{t}.{c}",
            "to": f"{rt}.{rc}",
            "declared": False,
        })
    return inferred


# ============================================================
# 4. Prompt building
# ============================================================

DIALECT_DATE_FUNCS = {
    "sqlite": ("date()", "datetime()", "strftime()", "julianday()",
               "Example: strftime('%Y-%m', order_purchase_timestamp)"),
    "postgresql": ("DATE_TRUNC()", "EXTRACT()", "TO_CHAR()",
                   "Example: DATE_TRUNC('month', order_purchase_timestamp)"),
    "mysql": ("DATE()", "YEAR()", "MONTH()", "DATE_FORMAT()",
              "Example: DATE_FORMAT(order_purchase_timestamp, '%Y-%m')"),
    "mariadb": ("DATE()", "YEAR()", "MONTH()", "DATE_FORMAT()",
                "Example: DATE_FORMAT(order_purchase_timestamp, '%Y-%m')"),
    "mssql": ("DATEPART()", "FORMAT()", "CAST(... AS DATE)",
              "Example: FORMAT(order_purchase_timestamp, 'yyyy-MM')"),
    "oracle": ("TRUNC()", "TO_CHAR()", "EXTRACT()",
               "Example: TO_CHAR(order_purchase_timestamp, 'YYYY-MM')"),
}


def build_prompt(url: str, sample_rows: int = 0,
                 include_system: bool = False) -> str:
    """Return a full, LLM-ready prompt describing the DB."""
    engine = create_engine(url)
    dialect = engine.dialect.name
    db_name = engine.url.database
    engine.dispose()

    schema = read_schema(url, include_system=include_system)
    relations = merge_relations(schema)

    lines = []
    lines.append(
        f"You are a {dialect.upper()} SQL expert. "
        f"Given the schema below, write correct {dialect.upper()} SQL.\n"
    )

    # ---- Schema ----
    lines.append("## SCHEMA\n")
    for table in sorted(schema):
        lines.append(f"### {table}")
        for col in schema[table]["columns"]:
            flags = []
            if col["pk"]:
                flags.append("PK")
            if col["not_null"]:
                flags.append("NOT NULL")
            if col["unique"]:
                flags.append("UNIQUE")
            if col["autoincrement"]:
                flags.append("AUTOINC")
            flag_str = f" [{' | '.join(flags)}]" if flags else ""

            role = infer_role(table, col["name"], col["category"])
            role_str = f"   -- {role}" if role else ""

            lines.append(
                f"  - {col['name']} {col['type']}{flag_str}{role_str}"
            )
        lines.append("")

    # ---- Relations ----
    if relations:
        declared = any(r["declared"] for r in relations)
        header = ("declared foreign keys" if declared
                  else "inferred from column naming; NOT enforced by the DB")
        lines.append(f"## RELATIONS ({header})\n")
        for r in relations:
            lines.append(f"  {r['from']} -> {r['to']}")
        lines.append("")

    # ---- Type mapping ----
    lines.append("## TYPE MAPPING\n")
    lines.append("  - integer: whole number")
    lines.append("  - float: approximate number; may have precision artifacts")
    lines.append("  - decimal: exact numeric; use for money")
    lines.append("  - string / text: character data")
    lines.append("  - boolean: TRUE/FALSE or 0/1")
    lines.append("  - date / datetime / time: temporal")
    lines.append("  - json: structured object")
    lines.append("  - binary: raw bytes")
    lines.append("")

    # ---- Column-type caveats ----
    lines.append("## COLUMN TYPE CAVEATS\n")
    # Datetime stored as string
    if any(c.get("name") and c["category"] == "string"
           and re.search(_DATETIME_NAME_RE, c["name"])
           for info in schema.values() for c in info["columns"]):
        lines.append("  - Some datetime columns are stored as TEXT. "
                     "Use the dialect's date functions.")
    # Money
    money_hits = [
        f"{t}.{c['name']}"
        for t, info in schema.items()
        for c in info["columns"]
        if _MONEY_NAME_RE.search(c["name"])
        and c["category"] in ("float", "integer", "decimal")
    ]
    if money_hits:
        lines.append(f"  - Money columns: {', '.join(money_hits[:8])}"
                     f"{' ...' if len(money_hits) > 8 else ''}")
        lines.append("    Wrap aggregates in ROUND(..., 2).")
    # FKs
    if relations and not any(r["declared"] for r in relations):
        lines.append("  - No enforced foreign keys. Use RELATIONS as join hints.")
    # IDs
    id_cols = [
        f"{t}.{c['name']}"
        for t, info in schema.items()
        for c in info["columns"]
        if _ID_NAME_RE.search(c["name"]) and c["category"] == "string"
    ]
    if id_cols:
        lines.append(f"  - String IDs: {', '.join(id_cols[:5])}"
                     f"{' ...' if len(id_cols) > 5 else ''}")
        lines.append("    Compare with quoted strings: id = 'abc123'.")
    lines.append("")

    # ---- Query rules ----
    lines.append("## QUERY RULES\n")
    lines.append(f"  1. Output ONLY valid {dialect.upper()} SQL "
                 "(no markdown, no comments).")
    lines.append("  2. Use explicit JOIN ... ON clauses.")
    lines.append("  3. Use ROUND(..., 2) for money aggregates.")
    lines.append("  4. Use LIMIT/FETCH when the user asks for top-N.")
    lines.append("  5. Never invent columns not listed in the schema.")
    lines.append("  6. If the question is ambiguous, ask one clarifying question.")

    # Dialect-specific date hint
    if dialect in DIALECT_DATE_FUNCS:
        funcs = DIALECT_DATE_FUNCS[dialect]
        lines.append(f"  7. Date functions: {', '.join(funcs[:-1])}. {funcs[-1]}")
    lines.append("")

    # ---- Sample rows ----
    if sample_rows > 0:
        lines.append("## SAMPLE ROWS\n")
        engine = create_engine(url)
        with engine.connect() as conn:
            for table in sorted(schema):
                try:
                    res = conn.execute(
                        text(f"SELECT * FROM {table} LIMIT {sample_rows}")
                    )
                    rows = [dict(r._mapping) for r in res]
                except Exception as e:
                    rows = [{"error": str(e)}]
                lines.append(f"### {table}")
                lines.append(json.dumps(rows, indent=2, default=str))
                lines.append("")
        engine.dispose()

    # ---- User question slot ----
    lines.append("## USER QUESTION\n")
    lines.append("{question}")

    return "\n".join(lines)


# ============================================================
# 5. CLI
# ============================================================

def main():
    p = argparse.ArgumentParser(
        description="Build an LLM-ready schema prompt for any database.")
    p.add_argument("--url", required=True,
                   help="SQLAlchemy URL. Examples:\n"
                        "  sqlite:///data/olist.db\n"
                        "  postgresql://user:pass@localhost:5432/mydb\n"
                        "  mysql+pymysql://user:pass@localhost:3306/mydb\n"
                        "  mssql+pyodbc://user:pass@dsn")
    p.add_argument("--samples", type=int, default=0,
                   help="Include N sample rows per table")
    p.add_argument("--system", action="store_true",
                   help="Include system tables")
    p.add_argument("--out", default="prompt_schema.txt")
    args = p.parse_args()

    prompt = build_prompt(args.url, sample_rows=args.samples,
                          include_system=args.system)
    Path(args.out).write_text(prompt, encoding="utf-8")
    print(f"Wrote {args.out} ({len(prompt)} chars)")
    print("\n----- PREVIEW (first 40 lines) -----\n")
    print("\n".join(prompt.splitlines()[:40]))


if __name__ == "__main__":
    main()