"""query_network_data tool: read-only SQL over the drive-test database (Analyst agent)."""
from __future__ import annotations

import importlib.util
import re
import sqlite3
import time
from pathlib import Path

from langchain_core.tools import tool

from .. import domain as d
from ..config import REPO_ROOT, get_settings

MAX_ROWS = 50
MAX_VALUE_BYTES = 100_000  # SQLite SQLITE_LIMIT_LENGTH: largest string or blob a query may build
MAX_OUTPUT_CHARS = 8_000   # cap on the text table returned to the LLM
QUERY_TIMEOUT_S = 2.0  # wall-clock budget per query (stops runaway recursive CTEs and cross joins)
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex|truncate)\b|\breplace\s+into\b",
    re.IGNORECASE,
)
STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")


def ensure_database(db_path: Path | None = None) -> Path:
    """Generate the synthetic database with data/generate_data.py if it does not exist yet."""
    path = Path(db_path or get_settings().db_path)
    if not path.exists():
        spec = importlib.util.spec_from_file_location("generate_data", REPO_ROOT / "data" / "generate_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate(path, scenarios_path=None)
    return path


def validate_sql(sql: str) -> str:
    """Return the cleaned statement, or raise ValueError if it is not a single read-only SELECT."""
    stmt = sql.strip().rstrip(";").strip()
    code = STRING_LITERAL.sub("''", stmt)  # keywords inside string literals are data, not SQL
    if not stmt:
        raise ValueError("empty query")
    if ";" in code:
        raise ValueError("only a single statement is allowed")
    if not re.match(r"^(select|with)\b", code, re.IGNORECASE):
        raise ValueError("only SELECT (or WITH ... SELECT) queries are allowed")
    if FORBIDDEN.search(code):
        raise ValueError("write or schema keywords are not allowed")
    return stmt


def run_query(sql: str, db_path: Path | None = None, max_rows: int = MAX_ROWS,
              timeout_s: float = QUERY_TIMEOUT_S) -> dict:
    """Execute a validated query on a read-only connection; returns columns, rows and truncation flag.

    A progress handler aborts the query after timeout_s ("interrupted"), so no query can hang the request.
    """
    stmt = validate_sql(sql)
    path = ensure_database(db_path)
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    if hasattr(conn, "setlimit"):  # Python 3.11+: huge strings or blobs fail fast instead of filling memory
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_VALUE_BYTES)
    deadline = time.monotonic() + timeout_s
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
    try:
        cur = conn.execute(stmt)
        columns = [c[0] for c in cur.description or []]
        rows = cur.fetchmany(max_rows + 1)
    finally:
        conn.close()
    return {"columns": columns, "rows": [list(r) for r in rows[:max_rows]], "truncated": len(rows) > max_rows}


def format_result(result: dict) -> str:
    """Compact text table for the LLM, at most MAX_OUTPUT_CHARS characters (plus the row note)."""
    lines = [" | ".join(result["columns"])]
    lines += [" | ".join(str(round(v, 3) if isinstance(v, float) else v) for v in row) for row in result["rows"]]
    note = f"\n({len(result['rows'])} rows" + (f", truncated at {MAX_ROWS}: aggregate instead)" if result["truncated"] else ")")
    table = "\n".join(lines)
    if len(table) > MAX_OUTPUT_CHARS:
        table = table[:MAX_OUTPUT_CHARS] + "\n(output truncated)"
    return table + note


QUERY_DESCRIPTION = f"""Run ONE read-only SQLite SELECT on the NordTel drive-test database. At most {MAX_ROWS} rows
are returned, so prefer aggregates (AVG, MIN, MAX, COUNT, GROUP BY) over raw rows.
Schema:
{d.DB_SCHEMA}
Drive-test routes are identified by route_id (e.g. 'R1'). A handover is a serving_pci change between
consecutive timestamps (use LAG(serving_pci) OVER (PARTITION BY route_id ORDER BY timestamp)).
Returns the rows as a text table, or an error with the schema."""


@tool(description=QUERY_DESCRIPTION)
def query_network_data(sql: str) -> str:
    """Read-only SQL query (full description in QUERY_DESCRIPTION)."""
    try:
        return format_result(run_query(sql))
    except (ValueError, sqlite3.Error) as exc:
        return f"Error: {exc}\nSchema:\n{d.DB_SCHEMA}"
