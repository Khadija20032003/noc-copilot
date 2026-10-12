"""Generate the synthetic NordTel drive-test database (deterministic, stdlib only).

Creates data/nordtel.db with the tables `cells` and `measurements` (columns from
docs/kb_style_guide.md, plus `route_id`) and writes data/scenarios.json, the ground truth
per route used by the evaluation. Each drive-test route plants ONE clear root cause, and one
route is healthy. All thresholds come from backend/app/domain.py.

Usage (from the repository root):  python data/generate_data.py
"""
from __future__ import annotations

import json
import math
import random
import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_DIR.parent / "backend"))

from app import domain as d  # noqa: E402

SEED = 42
DB_PATH = DATA_DIR / "nordtel.db"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"

# pci, site_name, latitude, longitude, azimuth_deg, downtilt_deg, frequency_mhz, bandwidth_mhz
CELLS = [
    (101, "STO-Sodermalm", 59.3135, 18.0710, 30, 6, 3500, 100),
    (102, "STO-Sodermalm", 59.3135, 18.0710, 150, 6, 3500, 100),
    (103, "STO-Sodermalm", 59.3135, 18.0710, 270, 6, 3500, 100),
    (204, "STO-Norrmalm", 59.3345, 18.0630, 60, 6, 3500, 100),
    (205, "STO-Norrmalm", 59.3345, 18.0630, 180, 6, 3500, 100),
    (307, "STO-Kungsholmen", 59.3290, 18.0330, 90, 2, 3500, 100),
    (145, "STO-Ostermalm", 59.3375, 18.0890, 240, 6, 3500, 100),
    (412, "STO-Vasastan", 59.3440, 18.0450, 120, 4, 700, 10),  # low-band layer, other frequency
]
CELL_BY_PCI = {c[0]: c for c in CELLS}

MEAS_COLUMNS = [
    "route_id", "timestamp", "serving_pci", "dl_throughput_mbps", "ss_rsrp_dbm", "ss_sinr_db",
    "ss_rsrq_db", "neighbor_pci", "neighbor_rsrp_dbm", "ue_speed_kmh", "scheduled_rbs",
    "latitude", "longitude",
]


def offset(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Move a point by metres north and east."""
    return lat + north_m / 111_320, lon + east_m / (111_320 * math.cos(math.radians(lat)))


class RouteBuilder:
    """Builds one route: a UE moving in a straight line, one row per second."""

    def __init__(self, rng: random.Random, route_id: str, start: str, site_pci: int,
                 north_m: float, east_m: float, heading_deg: float):
        self.rng, self.route_id, self.start = rng, route_id, start
        cell = CELL_BY_PCI[site_pci]
        self.lat, self.lon = offset(cell[2], cell[3], north_m, east_m)
        self.heading = math.radians(heading_deg)
        self.rows: list[tuple] = []

    def g(self, mean: float, sd: float, lo: float | None = None, hi: float | None = None) -> float:
        """Gaussian sample, clamped."""
        v = self.rng.gauss(mean, sd)
        if lo is not None:
            v = max(lo, v)
        if hi is not None:
            v = min(hi, v)
        return v

    def add(self, serving: int, tp: float, rsrp: float, sinr: float, rsrq: float,
            neighbor: int, n_rsrp: float, speed: float, rbs: float) -> None:
        """Append one row, then move the UE by one second at `speed`."""
        t = len(self.rows)
        hh, mm = self.start.split(":")
        total = int(hh) * 3600 + int(mm) * 60 + t
        ts = f"2026-09-15T{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
        self.rows.append((
            self.route_id, ts, serving, round(tp, 1), round(rsrp, 1), round(sinr, 1), round(rsrq, 1),
            neighbor, round(n_rsrp, 1), round(speed, 1), int(round(rbs)),
            round(self.lat, 6), round(self.lon, 6),
        ))
        step = speed / 3.6
        self.lat, self.lon = offset(self.lat, self.lon, step * math.cos(self.heading), step * math.sin(self.heading))


def route_healthy(rng: random.Random) -> list[tuple]:
    """R1: healthy route near STO-Sodermalm, all KPIs Good, throughput above target."""
    r = RouteBuilder(rng, "R1", "09:00", 101, 220, 130, 45)
    for _ in range(60):
        rsrp = r.g(-78, 1.5)
        r.add(101, r.g(860, 45, 650), rsrp, r.g(20, 1.5, 14), r.g(-8, 0.6, hi=-6), 102,
              rsrp - r.g(14, 2, 8), r.g(25, 2), r.g(250, 8, 220, 273))
    return r.rows


def route_overshooting(rng: random.Random) -> list[tuple]:
    """R2: RC2 Overshooting, UE served by STO-Kungsholmen PCI 307 (downtilt 2) from about 1.4 to 1.7 km."""
    r = RouteBuilder(rng, "R2", "09:30", 307, -200, 1400, 90)
    for t in range(60):
        rsrp = -102 - 8 * t / 59 + r.g(0, 1)
        r.add(307, r.g(320 - 2 * t, 30, 120, 450), rsrp, r.g(4 - 4 * t / 59, 1.2), r.g(-13 - 3 * t / 59, 0.6),
              204, rsrp - r.g(8, 1.5, 5), r.g(20, 1.5), r.g(235, 8, 210, 273))
    return r.rows


def route_pci_conflict(rng: random.Random) -> list[tuple]:
    """R3: RC6, serving PCI 205 with strong co-frequency neighbor PCI 145 (both PCI mod 30 = 25)."""
    r = RouteBuilder(rng, "R3", "10:00", 205, -150, 300, 90)
    for _ in range(60):
        rsrp = r.g(-88, 1.5)
        r.add(205, r.g(250, 40, 120, 400), rsrp, r.g(0.8, 1.3, -3, 4.5), r.g(-13.5, 0.7, -14.9),
              145, rsrp - r.g(1.5, 0.7, 0.3, 2.8), r.g(15, 1.5), r.g(240, 8, 215, 273))
    return r.rows


def route_low_rbs(rng: random.Random) -> list[tuple]:
    """R4: RC8 Low scheduled resources, good radio on PCI 102 but about 110 scheduled RBs."""
    r = RouteBuilder(rng, "R4", "10:30", 102, -250, 150, 180)
    for _ in range(60):
        rsrp = r.g(-82, 1.5)
        rbs = r.g(110, 14, 80, 145)
        r.add(102, rbs * 3.0 + r.g(0, 20), rsrp, r.g(16, 1.5, 13.5), r.g(-9, 0.6, -11.5),
              103, rsrp - r.g(12, 2, 7), r.g(10, 1), rbs)
    return r.rows


def route_high_speed(rng: random.Random) -> list[tuple]:
    """R5: RC7 High UE speed, about 70 km/h past STO-Norrmalm on PCI 204, fluctuating SINR."""
    r = RouteBuilder(rng, "R5", "11:00", 204, 200, -450, 90)
    for _ in range(50):
        rsrp = r.g(-90, 2.5, -100, -84)
        r.add(204, r.g(420, 80, 220, 580), rsrp, r.g(9, 3.5, 1.5, 17), r.g(-11, 1.2, -14.5),
              412, rsrp - r.g(6, 2, 4), r.g(70, 4, 55), r.g(225, 10, 200, 273))
    return r.rows


def route_frequent_handovers(rng: random.Random) -> list[tuple]:
    """R6: RC5 Frequent handovers with ping-pong between colocated PCIs 101 and 102.

    Throughput is above target except around the handovers, so RC5 explains every low sample."""
    r = RouteBuilder(rng, "R6", "11:30", 101, 0, 400, 0)
    handovers = {12: 102, 16: 101, 28: 102, 32: 101, 46: 102}  # second -> new serving PCI
    serving = 101
    for t in range(60):
        serving = handovers.get(t, serving)
        dip = t in handovers or (t - 1) in handovers
        rsrp = r.g(-86, 1.2)
        tp = r.g(200, 30, 120) if dip else r.g(760, 40, 650, 860)
        r.add(serving, tp, rsrp, r.g(7.5, 1, 5.5), r.g(-11.5, 0.6, -14),
              102 if serving == 101 else 101, rsrp - r.g(1.5, 0.7, 0.2, 2.8), r.g(15, 1.5), r.g(220, 8, 200, 273))
    return r.rows


ROUTES = [route_healthy, route_overshooting, route_pci_conflict, route_low_rbs, route_high_speed,
          route_frequent_handovers]

TRUTH = {
    "R1": (None, None, "Healthy reference route: all radio KPIs Good and throughput above target."),
    "R2": ("RC2", "P3", "UE served by PCI 307 (STO-Kungsholmen, downtilt 2) at more than 1 km."),
    "R3": ("RC6", "P3", "Serving PCI 205 and strong co-frequency neighbor PCI 145 share PCI mod 30 = 25; poor SINR."),
    "R4": ("RC8", "P3", "Average scheduled RBs below 160 with no radio KPI in the Poor band."),
    "R5": ("RC7", "P3", "UE speed above 40 km/h during the low throughput samples."),
    "R6": ("RC5", "P3", "3 or more serving_pci changes within 60 s, with ping-pong between PCIs 101 and 102."),
}


def summarize(rows: list[tuple]) -> dict:
    """Route statistics written to scenarios.json as evidence."""
    col = {name: i for i, name in enumerate(MEAS_COLUMNS)}
    n = len(rows)

    def avg(name: str) -> float:
        return round(sum(r[col[name]] for r in rows) / n, 1)

    dists = []
    for r in rows:
        cell = CELL_BY_PCI[r[col["serving_pci"]]]
        dists.append(d.haversine_km(r[col["latitude"]], r[col["longitude"]], cell[2], cell[3]))
    changes = sum(1 for a, b in zip(rows, rows[1:]) if a[col["serving_pci"]] != b[col["serving_pci"]])
    return {
        "rows": n,
        "time_range": [rows[0][col["timestamp"]], rows[-1][col["timestamp"]]],
        "serving_pcis": sorted({r[col["serving_pci"]] for r in rows}),
        "neighbor_pcis": sorted({r[col["neighbor_pci"]] for r in rows}),
        "avg_dl_throughput_mbps": avg("dl_throughput_mbps"),
        "avg_ss_rsrp_dbm": avg("ss_rsrp_dbm"),
        "avg_ss_sinr_db": avg("ss_sinr_db"),
        "avg_ss_rsrq_db": avg("ss_rsrq_db"),
        "avg_scheduled_rbs": avg("scheduled_rbs"),
        "avg_ue_speed_kmh": avg("ue_speed_kmh"),
        "min_serving_distance_km": round(min(dists), 2),
        "max_serving_distance_km": round(max(dists), 2),
        "serving_pci_changes": changes,
    }


def check_invariants(all_rows: list[tuple]) -> None:
    """Exactly one observed serving/neighbor pair has a PCI mod 30 conflict (205/145)."""
    pairs = {(r[2], r[7]) for r in all_rows}
    conflicts = {p for p in pairs if p[0] % d.PCI_MOD == p[1] % d.PCI_MOD}
    assert conflicts == {(205, 145)}, f"unexpected PCI mod 30 conflicts: {conflicts}"


def generate(db_path: Path = DB_PATH, scenarios_path: Path | None = SCENARIOS_PATH) -> Path:
    """Create the database (overwriting it) and optionally the scenarios ground truth."""
    rng = random.Random(SEED)
    per_route: dict[str, list[tuple]] = {}
    for fn in ROUTES:
        rows = fn(rng)
        per_route[rows[0][0]] = rows
    all_rows = [r for rows in per_route.values() for r in rows]
    check_invariants(all_rows)

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE cells (pci INTEGER PRIMARY KEY, site_name TEXT, latitude REAL, longitude REAL,"
            " azimuth_deg REAL, downtilt_deg REAL, frequency_mhz INTEGER, bandwidth_mhz INTEGER)"
        )
        conn.execute(
            "CREATE TABLE measurements (route_id TEXT, timestamp TEXT, serving_pci INTEGER,"
            " dl_throughput_mbps REAL, ss_rsrp_dbm REAL, ss_sinr_db REAL, ss_rsrq_db REAL,"
            " neighbor_pci INTEGER, neighbor_rsrp_dbm REAL, ue_speed_kmh REAL, scheduled_rbs INTEGER,"
            " latitude REAL, longitude REAL)"
        )
        conn.executemany("INSERT INTO cells VALUES (?,?,?,?,?,?,?,?)", CELLS)
        conn.executemany(f"INSERT INTO measurements VALUES ({','.join('?' * len(MEAS_COLUMNS))})", all_rows)

    if scenarios_path is not None:
        scenarios = {}
        for route_id, rows in per_route.items():
            rc, severity, evidence = TRUTH[route_id]
            stats = summarize(rows)
            scenarios[route_id] = {
                "expected_root_cause": rc,
                "root_cause_name": d.ROOT_CAUSES[rc] if rc else None,
                "expected_severity": severity,
                "serving_pci": stats["serving_pcis"][0],
                "site_name": CELL_BY_PCI[stats["serving_pcis"][0]][1],
                "evidence": evidence,
                "stats": stats,
            }
        Path(scenarios_path).write_text(json.dumps(scenarios, indent=2) + "\n", encoding="utf-8")
    return db_path


if __name__ == "__main__":
    path = generate()
    print(f"Wrote {path} and {SCENARIOS_PATH}")
