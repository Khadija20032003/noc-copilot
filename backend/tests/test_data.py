"""Data generator invariants: deterministic, schema as in the style guide, planted causes detectable."""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

from app.config import REPO_ROOT

STYLE_CELLS = ["pci", "site_name", "latitude", "longitude", "azimuth_deg", "downtilt_deg", "frequency_mhz",
               "bandwidth_mhz"]
STYLE_MEAS = ["timestamp", "serving_pci", "dl_throughput_mbps", "ss_rsrp_dbm", "ss_sinr_db", "ss_rsrq_db",
              "neighbor_pci", "neighbor_rsrp_dbm", "ue_speed_kmh", "scheduled_rbs", "latitude", "longitude"]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gen = load_module("generate_data", REPO_ROOT / "data" / "generate_data.py")
run_eval = load_module("run_eval", REPO_ROOT / "eval" / "run_eval.py")


def columns(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def test_schema_and_size(tmp_path):
    db = gen.generate(tmp_path / "t.db", scenarios_path=None)
    with sqlite3.connect(db) as conn:
        assert columns(conn, "cells") == STYLE_CELLS
        assert columns(conn, "measurements") == ["route_id"] + STYLE_MEAS
        n = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
        freqs = {r[0] for r in conn.execute("SELECT DISTINCT frequency_mhz FROM cells")}
    assert 200 <= n <= 600
    assert 3500 in freqs and len(freqs) >= 2


def test_deterministic(tmp_path):
    a = gen.generate(tmp_path / "a.db", scenarios_path=None)
    b = gen.generate(tmp_path / "b.db", scenarios_path=None)
    q = "SELECT * FROM measurements ORDER BY route_id, timestamp"
    with sqlite3.connect(a) as ca, sqlite3.connect(b) as cb:
        assert ca.execute(q).fetchall() == cb.execute(q).fetchall()


def test_scenarios_file_matches_generator(tmp_path):
    out = tmp_path / "s.json"
    gen.generate(tmp_path / "t.db", scenarios_path=out)
    assert json.loads(out.read_text()) == json.loads((REPO_ROOT / "data" / "scenarios.json").read_text())


def test_planted_root_causes_detectable_with_tools(tmp_path):
    db = gen.generate(tmp_path / "t.db", scenarios_path=None)
    results = run_eval.scenario_checks(db)
    assert {r["route"] for r in results} == {"R1", "R2", "R3", "R4", "R5", "R6"}
    failed = [r for r in results if not r["passed"]]
    assert not failed, failed


def test_exactly_one_pci_mod30_conflict_pair(tmp_path):
    db = gen.generate(tmp_path / "t.db", scenarios_path=None)
    with sqlite3.connect(db) as conn:
        pairs = conn.execute("SELECT DISTINCT serving_pci, neighbor_pci FROM measurements").fetchall()
    assert [p for p in pairs if p[0] % 30 == p[1] % 30] == [(205, 145)]
