"""Evaluation harness for NOC Copilot.

Run from the repository root:
  python eval/run_eval.py --offline   no LLM, no API key: retrieval metrics + data sanity check on the planted routes
  python eval/run_eval.py             full: runs the agent graph on every golden question (needs an API key)

Both modes write a Markdown report (eval/results_offline.md or eval/results.md). The offline mode exits
non-zero when a pass criterion fails; the full mode only reports (it fails only if no LLM is configured).
All metrics are simple and deterministic (no LLM-as-judge).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import domain as d  # noqa: E402
from app.rag import get_retriever  # noqa: E402
from app.tools.calculator import calculate  # noqa: E402
from app.tools.network_data import ensure_database, run_query  # noqa: E402

EVAL_DIR = ROOT / "eval"
GOLDEN = EVAL_DIR / "golden.jsonl"
SCENARIOS = ROOT / "data" / "scenarios.json"
K = 4
MIN_HIT_AT_K = 0.8
WORKER_AGENTS = {"Research", "Analyst"}


def load_golden() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------- offline: retrieval
def retrieval_metrics(items: list[dict], k: int = K) -> dict:
    """hit@k and MRR over expected source documents, on the RAG items only.

    RAG questions are what the Research agent would search for; multi-agent questions are not, because in
    the real flow the retriever sees the Supervisor's rewritten task. Those are scored in full mode instead.
    """
    retriever = get_retriever()
    rows = []
    for item in items:
        if item["category"] != "rag":
            continue
        docs = [chunk.doc for chunk, _ in retriever.search(item["question"], k=k)]
        rank = next((i + 1 for i, doc in enumerate(docs) if doc in item["expected_sources"]), None)
        rows.append({"id": item["id"], "rank": rank, "retrieved": docs})
    n = len(rows)
    return {
        "n": n,
        "hit_at_k": sum(r["rank"] is not None for r in rows) / n,
        "mrr": sum(1 / r["rank"] for r in rows if r["rank"]) / n,
        "rows": rows,
    }


# ---------------------------------------------------------------- offline: data sanity check per route
def detect_root_causes(route_id: str, db_path: Path) -> tuple[set[str], dict]:
    """Apply the runbook rules to one route using the tools' own implementations (SQL + calculator).

    This checks that the generated data and the rules agree (each planted cause is detectable and unique).
    It is a data sanity check, not an agent metric: the agents are only scored in full mode.
    """
    q = lambda sql: run_query(sql, db_path, max_rows=10_000)["rows"]  # noqa: E731
    rid = route_id.replace("'", "")
    agg = q(f"""SELECT AVG(scheduled_rbs), MIN(ss_rsrp_dbm), MIN(ss_sinr_db), MIN(ss_rsrq_db),
                SUM(dl_throughput_mbps < {d.DL_THROUGHPUT_TARGET_MBPS}),
                AVG(CASE WHEN dl_throughput_mbps < {d.DL_THROUGHPUT_TARGET_MBPS} THEN ue_speed_kmh END)
                FROM measurements WHERE route_id = '{rid}'""")[0]
    avg_rbs, min_rsrp, min_sinr, min_rsrq, low_rows, low_speed = agg
    evidence: dict = {"low_throughput_rows": low_rows, "avg_scheduled_rbs": round(avg_rbs, 1)}
    found: set[str] = set()
    if not low_rows:
        return found, evidence

    # RC2: distance from the average UE position to each serving cell.
    for pci, lat, lon, clat, clon in q(f"""SELECT m.serving_pci, AVG(m.latitude), AVG(m.longitude), c.latitude, c.longitude
            FROM measurements m JOIN cells c ON c.pci = m.serving_pci
            WHERE m.route_id = '{rid}' GROUP BY m.serving_pci"""):
        dist = calculate("distance_km", lat1=lat, lon1=lon, lat2=clat, lon2=clon)
        evidence[f"distance_km_pci_{pci}"] = dist["distance_km"]
        if dist["exceeds_overshooting_threshold"]:
            found.add("RC2")

    # RC6: strong co-frequency neighbor (3 dB rule in most rows) with the same PCI mod 30.
    for s_pci, n_pci, strong, total in q(f"""SELECT m.serving_pci, m.neighbor_pci,
            SUM(m.neighbor_rsrp_dbm >= m.ss_rsrp_dbm - {d.STRONG_NEIGHBOR_MARGIN_DB}), COUNT(*)
            FROM measurements m JOIN cells s ON s.pci = m.serving_pci JOIN cells n ON n.pci = m.neighbor_pci
            WHERE m.route_id = '{rid}' AND s.frequency_mhz = n.frequency_mhz
            GROUP BY m.serving_pci, m.neighbor_pci"""):
        if strong > total / 2 and calculate("pci_mod30", pci_a=s_pci, pci_b=n_pci)["conflict"]:
            evidence["pci_mod30_conflict"] = [s_pci, n_pci]
            found.add("RC6")

    # RC8: average RBs below 160 and no radio KPI in the Poor band (worst sample of each KPI).
    classes = [calculate("classify_kpi", kpi=k, value=v)["class"]
               for k, v in (("ss_rsrp_dbm", min_rsrp), ("ss_sinr_db", min_sinr), ("ss_rsrq_db", min_rsrq))]
    if avg_rbs < d.MIN_AVG_SCHEDULED_RBS and "Poor" not in classes:
        found.add("RC8")

    # RC7: high speed during the low throughput samples.
    evidence["avg_speed_low_rows_kmh"] = round(low_speed, 1)
    if low_speed > d.HIGH_SPEED_KMH:
        found.add("RC7")

    # RC5: 3 or more serving_pci changes in any sliding 60 s window.
    times = [r[0] for r in q(f"""SELECT CAST(strftime('%s', timestamp) AS INTEGER) FROM (
            SELECT timestamp, serving_pci, LAG(serving_pci) OVER (ORDER BY timestamp) AS prev
            FROM measurements WHERE route_id = '{rid}') WHERE prev IS NOT NULL AND prev != serving_pci""")]
    max_window = max((sum(1 for u in times if t <= u < t + d.FREQUENT_HO_WINDOW_S) for t in times), default=0)
    evidence["max_handovers_in_60s"] = max_window
    if max_window >= d.FREQUENT_HO_COUNT:
        found.add("RC5")
    return found, evidence


def scenario_checks(db_path: Path | None = None) -> list[dict]:
    """Every planted route must trigger exactly its expected root cause (healthy route: none)."""
    db = ensure_database(db_path)
    truth = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    results = []
    for route_id, t in truth.items():
        found, evidence = detect_root_causes(route_id, db)
        expected = {t["expected_root_cause"]} if t["expected_root_cause"] else set()
        results.append({"route": route_id, "expected": sorted(expected), "found": sorted(found),
                        "passed": found == expected, "evidence": evidence})
    return results


def run_offline() -> bool:
    items = load_golden()
    ret = retrieval_metrics(items)
    checks = scenario_checks()
    ok = ret["hit_at_k"] >= MIN_HIT_AT_K and all(c["passed"] for c in checks)

    lines = ["# Offline evaluation (no LLM)", "",
             f"Golden set: {len(items)} items. Retrieval: BM25, k={K}, over the {ret['n']} RAG items "
             "(expected sources = the documents that define the answer).", "",
             "| Metric | Value | Pass criterion |", "|---|---|---|",
             f"| Retrieval hit@{K} | {ret['hit_at_k']:.2f} | >= {MIN_HIT_AT_K} |",
             f"| Retrieval MRR | {ret['mrr']:.2f} | reported |",
             f"| Data sanity check (planted routes) | {sum(c['passed'] for c in checks)}/{len(checks)} | all |", "",
             "## Retrieval per item", "", "| Item | First relevant rank | Retrieved docs |", "|---|---|---|"]
    lines += [f"| {r['id']} | {r['rank'] or 'miss'} | {', '.join(r['retrieved'])} |" for r in ret["rows"]]
    lines += ["", "## Data sanity check: runbook rules applied with the tool implementations", "",
              "Checks that each planted root cause is detectable in the generated data (not an agent metric).", "",
              "| Route | Expected | Detected | Pass | Evidence |", "|---|---|---|---|---|"]
    lines += [f"| {c['route']} | {', '.join(c['expected']) or 'healthy'} | {', '.join(c['found']) or 'none'} | "
              f"{'yes' if c['passed'] else 'NO'} | {json.dumps(c['evidence'])} |" for c in checks]
    lines += ["", f"Overall: {'PASS' if ok else 'FAIL'}", ""]
    report = "\n".join(lines)
    (EVAL_DIR / "results_offline.md").write_text(report, encoding="utf-8")
    print(report)
    return ok


# ---------------------------------------------------------------- full: run the agent graph
def fact_found(fact: str | list[str], answer: str) -> bool:
    """A must_include fact is a string, or a list of accepted spellings (e.g. ["1.57", "1.6 km"])."""
    return any(f.lower() in answer for f in ([fact] if isinstance(fact, str) else fact))


def score_item(item: dict, result: dict, latency_s: float) -> dict:
    trace = result["trace"]
    agents = {t["agent"] for t in trace}
    # Tool selection scores the worker agents only: the Verifier's own searches do not count.
    tools = {t["detail"].split("(", 1)[0] for t in trace if t["type"] == "tool_call" and t["agent"] != "Verifier"}
    answer = result["answer"].lower()
    expected_workers = set(item["expected_agents"]) & WORKER_AGENTS
    verified = any(t["type"] == "verdict" for t in trace)
    facts = item["must_include"]
    cited_docs = {s.split(" > ")[0] for s in result["sources"]}
    return {
        "id": item["id"],
        "category": item["category"],
        "agents_ok": (agents & WORKER_AGENTS) == expected_workers,
        "verify_ok": verified == ("Verifier" in item["expected_agents"]),
        "tools_ok": set(item["expected_tools"]) <= tools,
        "root_cause_ok": None if not item["expected_root_cause"] else result.get("root_cause_id") == item["expected_root_cause"],
        "fact_recall": sum(fact_found(f, answer) for f in facts) / len(facts) if facts else 1.0,
        "source_hit": None if not item["expected_sources"] else bool(cited_docs & set(item["expected_sources"])),
        "approved": result.get("approved") if verified else None,
        "steps": result.get("steps", 0),
        "latency_s": round(latency_s, 1),
        "agents": sorted(agents),
        "tools": sorted(tools),
    }


def mean(values: list) -> float | None:
    values = [float(v) for v in values if v is not None]
    return statistics.mean(values) if values else None


def run_full() -> bool:
    from app.config import get_settings
    from app.graph import build_graph, run_turn
    from app.llm import MissingAPIKeyError, get_chat_model

    try:
        llm = get_chat_model()
    except MissingAPIKeyError as exc:
        print(f"Full evaluation needs an LLM. {exc}\nRun `python eval/run_eval.py --offline` for the no-LLM checks.")
        return False
    ensure_database()
    graph = build_graph(llm)
    scores = []
    for item in load_golden():
        session = f"eval-{item['id']}-{uuid.uuid4().hex[:6]}"
        start = time.perf_counter()
        try:
            for turn in item.get("turns", [item["question"]]):
                result = run_turn(graph, session, turn)
        except Exception as exc:  # noqa: BLE001 (report and continue)
            print(f"{item['id']}: ERROR {exc}")
            result = {"answer": "", "sources": [], "trace": [], "root_cause_id": None, "approved": None, "steps": 0}
        scores.append(score_item(item, result, time.perf_counter() - start))
        print(f"{item['id']}: {scores[-1]}")

    def pct(key: str) -> str:
        m = mean([s[key] for s in scores])
        return "n/a" if m is None else f"{m:.0%}"

    s = get_settings()
    lines = ["# Full evaluation", "", f"Model: {s.llm_provider} / {s.model_name}. Items: {len(scores)}.", "",
             "| Metric | Value |", "|---|---|",
             f"| Agent selection accuracy (Research/Analyst set matches) | {pct('agents_ok')} |",
             f"| Verification decision accuracy | {pct('verify_ok')} |",
             f"| Tool selection (expected tools called) | {pct('tools_ok')} |",
             f"| Root cause accuracy (diagnosis items) | {pct('root_cause_ok')} |",
             f"| must_include fact recall | {pct('fact_recall')} |",
             f"| Source citation hit | {pct('source_hit')} |",
             f"| Verifier approval rate | {pct('approved')} |",
             f"| Average supervisor steps | {mean([x['steps'] for x in scores]):.1f} |",
             f"| Average latency per item (s) | {mean([x['latency_s'] for x in scores]):.1f} |", "",
             "## Per item", "",
             "| Item | Agents | Verify | Tools | Root cause | Facts | Source | Approved | Steps | Latency (s) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    fmt = lambda v: "-" if v is None else ("yes" if v is True else "no" if v is False else v)  # noqa: E731
    for x in scores:
        lines.append(f"| {x['id']} | {fmt(x['agents_ok'])} | {fmt(x['verify_ok'])} | {fmt(x['tools_ok'])} | "
                     f"{fmt(x['root_cause_ok'])} | {x['fact_recall']:.0%} | {fmt(x['source_hit'])} | "
                     f"{fmt(x['approved'])} | {x['steps']} | {x['latency_s']} |")
    report = "\n".join(lines) + "\n"
    (EVAL_DIR / "results.md").write_text(report, encoding="utf-8")
    print(report)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="no LLM: retrieval and tool checks only")
    args = parser.parse_args()
    sys.exit(0 if (run_offline() if args.offline else run_full()) else 1)
