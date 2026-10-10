"""
db_inspect.py — List tables, columns (with types), and relations from any database.

Supports: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server

Install:
    pip install sqlalchemy
    # then the driver for your DB:
    pip install psycopg2-binary   # PostgreSQL
    pip install pymysql           # MySQL/MariaDB
    pip install pyodbc            # SQL Server
    # SQLite is built-in
"""

import argparse
from sqlalchemy import create_engine, inspect


def fmt_default(d):
    if d is None:
        return ""
    return f" DEFAULT {d}"


def inspect_db(url: str, show_system: bool = False):
    engine = create_engine(url)
    insp = inspect(engine)
    dialect = engine.dialect.name

    print(f"\n=== Database: {engine.url.database} ({dialect}) ===")
    print(f"=== Host: {engine.url.host or 'local'} ===\n")

    schema = None
    if dialect in ("postgresql", "mssql"):
        schema = insp.default_schema_name

    tables = insp.get_table_names(schema=schema)
    if not show_system:
        tables = [t for t in tables
                  if not t.startswith(("sqlite_", "pg_", "sys"))]

    if not tables:
        print("No tables found.")
        return

    for table in sorted(tables):
        print(f"Table: {table}")

        # ---------- Primary key ----------
        try:
            pk = insp.get_pk_constraint(table, schema=schema) or {}
        except Exception as e:
            pk = {}
            print(f"   (could not read PK: {e})")
        pk_cols = set(pk.get("constrained_columns") or [])

        # ---------- Unique constraints + unique indexes ----------
        uniques = set()
        try:
            for uc in insp.get_unique_constraints(table, schema=schema):
                for c in uc.get("column_names") or []:
                    uniques.add(c)
        except Exception:
            pass
        try:
            for idx in insp.get_indexes(table, schema=schema):
                if idx.get("unique"):
                    for c in idx.get("column_names") or []:
                        uniques.add(c)
        except Exception:
            pass

        # ---------- Columns ----------
        cols = insp.get_columns(table, schema=schema)
        print(f"   Columns ({len(cols)}):")
        for c in cols:
            name = c["name"]
            col_type = c["type"]
            py_type = type(col_type).__name__
            null_str = "NULL" if c.get("nullable", True) else "NOT NULL"

            flags = []
            if name in pk_cols:
                flags.append("PK")
            if name in uniques:
                flags.append("UNIQUE")
            if c.get("autoincrement"):
                flags.append("AUTOINC")

            default = fmt_default(c.get("default"))
            flag_str = f" [{' | '.join(flags)}]" if flags else ""

            print(f"      - {name}: {col_type} "
                  f"(python={py_type}, {null_str}{default}){flag_str}")

        # ---------- Foreign keys ----------
        try:
            fks = insp.get_foreign_keys(table, schema=schema)
        except Exception:
            fks = []

        if fks:
            print("   Relations (FKs):")
            for fk in fks:
                local = ", ".join(fk["constrained_columns"])
                ref_table = fk["referred_table"]
                ref_cols = ", ".join(fk["referred_columns"])
                opts = fk.get("options", {}) or {}
                parts = []
                if opts.get("onupdate"):
                    parts.append(f"ON UPDATE {opts['onupdate']}")
                if opts.get("ondelete"):
                    parts.append(f"ON DELETE {opts['ondelete']}")
                extra = " " + " ".join(parts) if parts else ""
                print(f"      {local} -> {ref_table}({ref_cols}){extra}")

        print()


def list_reverse_relations(url: str):
    engine = create_engine(url)
    insp = inspect(engine)

    incoming = {}
    for table in insp.get_table_names():
        try:
            fks = insp.get_foreign_keys(table)
        except Exception:
            fks = []
        for fk in fks:
            incoming.setdefault(fk["referred_table"], []).append(
                (table, fk["constrained_columns"], fk["referred_columns"])
            )

    if not incoming:
        print("=== Reverse relations: none declared in this DB ===")
        return

    print("=== Reverse relations (who references whom) ===")
    for target, refs in sorted(incoming.items()):
        print(f"\n{target} is referenced by:")
        for src, cols, ref_cols in refs:
            print(f"   <- {src}({', '.join(cols)}) -> "
                  f"{target}({', '.join(ref_cols)})")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect DB tables, columns, relations")
    parser.add_argument(
        "--url", required=True,
        help="SQLAlchemy URL. Examples:\n"
             "  sqlite:///data/olist.db\n"
             "  postgresql://user:pass@localhost:5432/mydb\n"
             "  mysql+pymysql://user:pass@localhost:3306/mydb\n"
             "  mssql+pyodbc://user:pass@dsn"
    )
    parser.add_argument("--system", action="store_true",
                        help="Include system tables")
    parser.add_argument("--reverse", action="store_true",
                        help="Also show reverse relations")
    args = parser.parse_args()

    inspect_db(args.url, show_system=args.system)

    if args.reverse:
        print()
        list_reverse_relations(args.url)


if __name__ == "__main__":
    main()