import sqlite3
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "olist.db"

st.set_page_config(page_title = "Prompt-to-SQL BI Tool", layout = 'wide')

st.title("Prompt-to SQL BI Tool")
st.caption("Day 1 — Database is loaded and ready.")

st.info("Open the sidebar to see the database contents.")

with st.sidebar:
    st.header("Database Stats")

    if not DB_PATH.exists():
        st.error("Database not found")
    else:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]

        st.markdown(f"**{len(tables)} tables** in `olist.db`")

        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                st.markdown(f"- `{t}` — **{count:,}** rows")
            except Exception as e:
                st.markdown(f"- `{t}` — ⚠️ {e}")

        conn.close()