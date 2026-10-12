"""Tools: read-only SQL, calculator, knowledge base search, ticket tool."""
import json
import sqlite3

import pytest

from app.tools import network_calculator, query_network_data, search_knowledge_base
from app.tools.calculator import calculate
from app.tools.network_data import MAX_OUTPUT_CHARS, run_query, validate_sql


@pytest.mark.parametrize("sql", [
    "INSERT INTO cells VALUES (1,'x',0,0,0,0,0,0)",
    "DROP TABLE cells",
    "SELECT 1; DROP TABLE cells",
    "SELECT * FROM cells; SELECT * FROM measurements",
    "UPDATE cells SET downtilt_deg = 0",
    "WITH x AS (SELECT 1) DELETE FROM cells",
    "PRAGMA table_info(cells)",
    "ATTACH DATABASE 'x.db' AS x",
    "",
])
def test_sql_rejects_non_select(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)
    assert query_network_data.invoke({"sql": sql}).startswith("Error:")


def test_sql_keywords_inside_string_literals_are_allowed():
    assert validate_sql("SELECT replace(site_name, 'STO-', '') FROM cells WHERE site_name NOT LIKE '%update%'")
    with pytest.raises(ValueError):
        validate_sql("SELECT 'a'; DROP TABLE cells")


def test_runaway_query_is_interrupted():
    sql = "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM r) SELECT COUNT(*) FROM r"
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        run_query(sql, timeout_s=0.2)
    out = query_network_data.invoke({"sql": sql})  # default 2 s budget, clean error for the agent
    assert out.startswith("Error: interrupted")


def test_sql_error_includes_schema():
    out = query_network_data.invoke({"sql": "SELECT nope FROM cells"})
    assert out.startswith("Error:") and "measurements(" in out


def test_sql_select_and_with():
    assert run_query("SELECT COUNT(*) FROM cells;")["rows"] == [[8]]
    res = run_query("WITH r AS (SELECT DISTINCT route_id FROM measurements) SELECT COUNT(*) FROM r")
    assert res["rows"] == [[6]]


def test_sql_row_cap():
    res = run_query("SELECT * FROM measurements")
    assert len(res["rows"]) == 50 and res["truncated"]


def test_sql_result_size_is_capped():
    # One huge value is rejected by SQLite itself (SQLITE_LIMIT_LENGTH), before it fills memory.
    assert query_network_data.invoke({"sql": "SELECT hex(zeroblob(3000000))"}).startswith("Error:")
    # Many large values: the text returned to the LLM is truncated.
    out = query_network_data.invoke({"sql": "SELECT hex(zeroblob(2000)) FROM measurements"})
    assert "(output truncated)" in out and len(out) < MAX_OUTPUT_CHARS + 100


def test_database_connection_is_read_only(database):
    conn = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM cells")
    conn.close()


def test_calculator_distance():
    out = calculate("distance_km", lat1=59.3290, lon1=18.0330, lat2=59.3290, lon2=18.0330)
    assert out["distance_km"] == 0
    # 0.01 degree of latitude is about 1.11 km
    out = calculate("distance_km", lat1=59.0, lon1=18.0, lat2=59.01, lon2=18.0)
    assert 1.10 < out["distance_km"] < 1.12 and out["exceeds_overshooting_threshold"]


def test_calculator_pci_mod30():
    assert calculate("pci_mod30", pci_a=205, pci_b=145)["conflict"] is True
    assert calculate("pci_mod30", pci_a=101, pci_b=102)["conflict"] is False


@pytest.mark.parametrize("kpi,value,expected", [
    ("ss_rsrp_dbm", -90, "Good"), ("rsrp", -90.1, "Fair"), ("RSRP", -105, "Fair"), ("ss_rsrp_dbm", -105.1, "Poor"),
    ("sinr", 13, "Good"), ("sinr", 0, "Fair"), ("sinr", -0.5, "Poor"),
    ("rsrq", -10, "Good"), ("rsrq", -15, "Fair"), ("rsrq", -15.5, "Poor"),
])
def test_calculator_classify(kpi, value, expected):
    assert calculate("classify_kpi", kpi=kpi, value=value)["class"] == expected


@pytest.mark.parametrize("args", [
    {"operation": "distance_km", "lat1": 59.0},
    {"operation": "distance_km", "lat1": 95, "lon1": 0, "lat2": 0, "lon2": 0},
    {"operation": "pci_mod30", "pci_a": 2000, "pci_b": 1},
    {"operation": "classify_kpi", "kpi": "cqi", "value": 3},
])
def test_calculator_errors_are_returned(args):
    assert network_calculator.invoke(args).startswith("Error:")


def test_calculator_tool_returns_json():
    out = json.loads(network_calculator.invoke({"operation": "pci_mod30", "pci_a": 205, "pci_b": 145}))
    assert out["pci_a_mod30"] == 25


def test_search_tool_returns_sources_artifact():
    msg = search_knowledge_base.invoke({"name": "search_knowledge_base", "args": {"query": "PCI mod 30 conflict"},
                                        "id": "c1", "type": "tool_call"})
    assert msg.artifact and all(" > " in s for s in msg.artifact)
    assert "[source: " in msg.content


def test_save_ticket_stores(tickets_file):
    from app.tools.tickets import TicketDraft, save_ticket

    ticket = save_ticket(TicketDraft(
        severity="P3", pci=205, neighbor_pci=145, site_name="STO-Norrmalm",
        symptom="DL throughput below 600 Mbps", evidence="avg 242 Mbps, SINR 0.5 dB",
        root_cause_id="RC6", recommended_action="PCI re-plan (RAN optimization team)", confidence="high",
    ))
    assert ticket.id.startswith("NT-")
    assert json.loads(tickets_file.read_text())[0]["pci"] == 205


def test_root_cause_ids_match_domain():
    from typing import get_args

    from pydantic import ValidationError

    from app import domain
    from app.agents import DraftAnswer
    from app.tools.tickets import RootCauseId

    assert set(get_args(RootCauseId)) == set(domain.ROOT_CAUSES)
    with pytest.raises(ValidationError):
        DraftAnswer(answer="x", root_cause_id="RC6 PCI mod 30 conflict")


def test_replace_into_rejected_but_replace_function_allowed():
    from app.tools.network_data import FORBIDDEN

    assert FORBIDDEN.search("WITH t AS (SELECT 1) REPLACE INTO cells VALUES (1)")
    assert not FORBIDDEN.search("SELECT replace(site_name, 'STO-', '') FROM cells")
