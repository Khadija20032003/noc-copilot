"""network_calculator tool: deterministic calculations so the LLM never does arithmetic itself."""
from __future__ import annotations

import json
from typing import Literal

from langchain_core.tools import tool

from .. import domain as d

def calculate(operation: str, **kw) -> dict:
    """Pure implementation behind the tool; raises ValueError on bad input."""
    def need(*names: str) -> list:
        missing = [n for n in names if kw.get(n) is None]
        if missing:
            raise ValueError(f"operation '{operation}' needs: {', '.join(missing)}")
        return [kw[n] for n in names]

    if operation == "distance_km":
        lat1, lon1, lat2, lon2 = (float(v) for v in need("lat1", "lon1", "lat2", "lon2"))
        dist = d.haversine_km(lat1, lon1, lat2, lon2)
        return {"distance_km": round(dist, 3), "overshooting_threshold_km": d.OVERSHOOT_DISTANCE_KM,
                "exceeds_overshooting_threshold": dist > d.OVERSHOOT_DISTANCE_KM}
    if operation == "pci_mod30":
        a, b = (int(v) for v in need("pci_a", "pci_b"))
        for pci in (a, b):
            if not 0 <= pci <= 1007:
                raise ValueError(f"PCI {pci} out of range 0 to 1007")
        return {"pci_a": a, "pci_a_mod30": a % d.PCI_MOD, "pci_b": b, "pci_b_mod30": b % d.PCI_MOD,
                "conflict": a % d.PCI_MOD == b % d.PCI_MOD}
    if operation == "classify_kpi":
        kpi, value = need("kpi", "value")
        column = d.resolve_kpi(str(kpi))
        t = d.KPI_THRESHOLDS[column]
        return {"kpi": column, "value": float(value), "class": d.classify_kpi(column, float(value)),
                "thresholds": f"Good >= {t['good_min']:g}, Poor < {t['poor_below']:g} {t['unit']}"}
    raise ValueError("operation must be one of: distance_km, pci_mod30, classify_kpi")


CALCULATOR_DESCRIPTION = f"""Exact network calculations with NordTel thresholds. Operations:
- distance_km: haversine distance between (lat1, lon1) and (lat2, lon2), e.g. UE to serving cell;
  flags distances above {d.OVERSHOOT_DISTANCE_KM:g} km (RC2 Overshooting).
- pci_mod30: PCI mod {d.PCI_MOD} of pci_a and pci_b and whether they conflict (RC6).
- classify_kpi: kpi ({', '.join(d.KPI_THRESHOLDS)}) and value -> Good, Fair or Poor.
Returns JSON, or an error message explaining what is wrong with the input."""


@tool(description=CALCULATOR_DESCRIPTION)
def network_calculator(
    operation: Literal["distance_km", "pci_mod30", "classify_kpi"],
    lat1: float | None = None, lon1: float | None = None,
    lat2: float | None = None, lon2: float | None = None,
    pci_a: int | None = None, pci_b: int | None = None,
    kpi: str | None = None, value: float | None = None,
) -> str:
    """Exact network calculations (full description in CALCULATOR_DESCRIPTION)."""
    args = dict(lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2, pci_a=pci_a, pci_b=pci_b, kpi=kpi, value=value)
    try:
        return json.dumps(calculate(operation, **args))
    except (ValueError, TypeError, KeyError) as exc:
        return f"Error: {exc}"
