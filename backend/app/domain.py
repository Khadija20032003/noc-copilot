"""NordTel domain constants: the single source of truth for thresholds, root causes and severities.

Every value here comes from docs/kb_style_guide.md and matches the knowledge base. The data
generator, the tools, the prompts and the evaluation all import from this module.
Stdlib only, so data/generate_data.py can import it without the backend dependencies.
"""
from __future__ import annotations

import math

# KPI thresholds (5G NR, SS-based). Good if value >= good_min, Poor if value < poor_below, else Fair.
KPI_THRESHOLDS: dict[str, dict[str, float | str]] = {
    "ss_rsrp_dbm": {"label": "SS-RSRP", "unit": "dBm", "good_min": -90.0, "poor_below": -105.0},
    "ss_sinr_db": {"label": "SS-SINR", "unit": "dB", "good_min": 13.0, "poor_below": 0.0},
    "ss_rsrq_db": {"label": "SS-RSRQ", "unit": "dB", "good_min": -10.0, "poor_below": -15.0},
}
KPI_ALIASES = {
    "rsrp": "ss_rsrp_dbm", "ss-rsrp": "ss_rsrp_dbm", "ss_rsrp": "ss_rsrp_dbm",
    "sinr": "ss_sinr_db", "ss-sinr": "ss_sinr_db", "ss_sinr": "ss_sinr_db",
    "rsrq": "ss_rsrq_db", "ss-rsrq": "ss_rsrq_db", "ss_rsrq": "ss_rsrq_db",
}

DL_THROUGHPUT_TARGET_MBPS = 600.0      # below this: low throughput event
MIN_AVG_SCHEDULED_RBS = 160            # RC8: average scheduled RBs below this is too low
MAX_RBS_100MHZ_30KHZ = 273             # carrier maximum the 160 RB rule assumes
OVERSHOOT_DISTANCE_KM = 1.0            # RC2: serving cell farther than this from the UE
HIGH_SPEED_KMH = 40.0                  # RC7: UE speed above this
FREQUENT_HO_COUNT = 3                  # RC5: this many handovers ...
FREQUENT_HO_WINDOW_S = 60              # ... within this sliding window
PING_PONG_RETURN_S = 5                 # return to the previous cell within this time
STRONG_NEIGHBOR_MARGIN_DB = 3.0        # neighbor RSRP within this margin of serving (or higher)
PCI_MOD = 30                           # RC6 planning check
DEFAULT_DOWNTILT_DEG = 6.0
TILT_STEP_DEG = (1, 2)                 # typical downtilt adjustment step
P2_DURATION_MIN = 30                   # P2(a): a cell below target for more than this
EARTH_RADIUS_KM = 6371.0

ROOT_CAUSES: dict[str, str] = {
    "RC1": "Downtilt too large",
    "RC2": "Overshooting",
    "RC3": "Better neighbor available",
    "RC4": "Overlapping coverage",
    "RC5": "Frequent handovers degrade performance",
    "RC6": "PCI mod 30 conflict between serving and neighbor cell causes interference",
    "RC7": "High UE speed (above 40 km/h)",
    "RC8": "Low scheduled resources",
}

SEVERITIES: dict[str, str] = {
    "P1": "Critical: site down, or more than 3 cells degraded in one area, or emergency service impact. Respond in 15 min.",
    "P2": "Major: any cell below 600 Mbps for more than 30 min, or a Poor KPI on a busy cell. Respond in 1 hour.",
    "P3": "Minor: intermittent or single-route degradation with a known cause. Respond in 1 business day.",
    "P4": "Planning: optimization suggestion, no customer impact. Next planning cycle.",
}

DB_SCHEMA = """\
cells(pci INTEGER, site_name TEXT, latitude REAL, longitude REAL, azimuth_deg REAL,
      downtilt_deg REAL, frequency_mhz INTEGER, bandwidth_mhz INTEGER)
measurements(route_id TEXT, timestamp TEXT ISO-8601 one row per second, serving_pci INTEGER,
      dl_throughput_mbps REAL, ss_rsrp_dbm REAL, ss_sinr_db REAL, ss_rsrq_db REAL,
      neighbor_pci INTEGER, neighbor_rsrp_dbm REAL, ue_speed_kmh REAL, scheduled_rbs INTEGER,
      latitude REAL, longitude REAL)
Join measurements.serving_pci (or neighbor_pci) = cells.pci. PCIs are unique in this test area."""


def resolve_kpi(name: str) -> str:
    """Map a KPI name or alias (e.g. 'RSRP', 'ss_sinr_db') to its column name."""
    key = name.strip().lower()
    key = KPI_ALIASES.get(key, key)
    if key not in KPI_THRESHOLDS:
        raise ValueError(f"Unknown KPI '{name}'. Use one of: {', '.join(KPI_THRESHOLDS)}")
    return key


def classify_kpi(name: str, value: float) -> str:
    """Classify a KPI value as Good, Fair or Poor with the NordTel thresholds."""
    t = KPI_THRESHOLDS[resolve_kpi(name)]
    if value >= t["good_min"]:
        return "Good"
    if value < t["poor_below"]:
        return "Poor"
    return "Fair"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in km (used by the generator and the calculator)."""
    for lat in (lat1, lat2):
        if not -90 <= lat <= 90:
            raise ValueError(f"latitude {lat} out of range [-90, 90]")
    for lon in (lon1, lon2):
        if not -180 <= lon <= 180:
            raise ValueError(f"longitude {lon} out of range [-180, 180]")
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def thresholds_summary() -> str:
    """Compact text of all thresholds, injected into prompts so agents use the NordTel values."""
    kpis = "; ".join(
        f"{t['label']} Good >= {t['good_min']:g} {t['unit']}, Poor < {t['poor_below']:g} {t['unit']}, Fair in between"
        for t in KPI_THRESHOLDS.values()
    )
    return (
        f"{kpis}. DL throughput target {DL_THROUGHPUT_TARGET_MBPS:g} Mbps. "
        f"RC8 if average scheduled RBs < {MIN_AVG_SCHEDULED_RBS} AND no radio KPI Poor; caveats: the "
        f"{MIN_AVG_SCHEDULED_RBS} RB rule assumes a 100 MHz carrier at 30 kHz SCS ({MAX_RBS_100MHZ_30KHZ} RBs max), "
        f"so on a narrower carrier compare against that carrier's maximum, and low RBs can mean the test was not "
        f"a full-buffer download (check the test type). "
        f"RC2 if serving cell > {OVERSHOOT_DISTANCE_KM:g} km from the UE. RC7 if UE speed > {HIGH_SPEED_KMH:g} km/h. "
        f"RC5 if >= {FREQUENT_HO_COUNT} handovers (serving_pci changes) within {FREQUENT_HO_WINDOW_S} s. "
        f"Ping-pong: the UE returns to the previous cell within {PING_PONG_RETURN_S} s. "
        f"Strong neighbor: neighbor RSRP within {STRONG_NEIGHBOR_MARGIN_DB:g} dB of serving or higher. "
        f"RC6 if serving and strong co-frequency neighbor share PCI mod {PCI_MOD}. "
        f"Default downtilt {DEFAULT_DOWNTILT_DEG:g} degrees, typical adjustment step {TILT_STEP_DEG[0]} to "
        f"{TILT_STEP_DEG[1]} degrees. P2(a) needs a cell below {DL_THROUGHPUT_TARGET_MBPS:g} Mbps for more than "
        f"{P2_DURATION_MIN} min."
    )
