# Data

Synthetic NordTel drive-test data (SQLite), generated deterministically (seed 42, stdlib only) by
`generate_data.py`. All thresholds are imported from `backend/app/domain.py`.

```bash
python data/generate_data.py   # writes data/nordtel.db (not committed) and data/scenarios.json
```

The backend also generates `nordtel.db` on first start if it is missing.

- `cells`: 8 cells on 5 sites around Stockholm (7 on 3500 MHz with 100 MHz, 1 on 700 MHz with 10 MHz).
- `measurements`: 350 rows, one per second, on 6 routes (`route_id` R1 to R6). Columns as in
  `docs/kb_style_guide.md`, plus `route_id`.
- `scenarios.json` (committed): ground truth per route (expected root cause, severity, evidence and
  statistics), used by the evaluation and the tests.

| Route | Planted root cause |
|---|---|
| R1 | none (healthy reference) |
| R2 | RC2 Overshooting (PCI 307 serves the UE from about 1.6 km) |
| R3 | RC6 PCI mod 30 conflict (serving 205, strong co-frequency neighbor 145) |
| R4 | RC8 Low scheduled resources (about 113 RBs, radio KPIs not Poor) |
| R5 | RC7 High UE speed (about 71 km/h) |
| R6 | RC5 Frequent handovers (ping-pong between 101 and 102; throughput only dips around the handovers) |

`tickets.json` (not committed) stores tickets approved in the UI.
