# Offline evaluation (no LLM)

Golden set: 20 items. Retrieval: BM25, k=4, over the 7 RAG items (expected sources = the documents that define the answer).

| Metric | Value | Pass criterion |
|---|---|---|
| Retrieval hit@4 | 1.00 | >= 0.8 |
| Retrieval MRR | 0.83 | reported |
| Data sanity check (planted routes) | 6/6 | all |

## Retrieval per item

| Item | First relevant rank | Retrieved docs |
|---|---|---|
| rag-01 | 1 | 5g_basics.md, runbook_interference.md, runbook_interference.md, kpi_glossary.md |
| rag-02 | 1 | kpi_glossary.md, kpi_glossary.md, kpi_glossary.md, kpi_glossary.md |
| rag-03 | 1 | runbook_interference.md, runbook_interference.md, runbook_interference.md, runbook_low_throughput.md |
| rag-04 | 1 | kpi_glossary.md, handover_basics.md, handover_basics.md, runbook_capacity_mobility.md |
| rag-05 | 1 | escalation_policy.md, escalation_policy.md, escalation_policy.md, 5g_basics.md |
| rag-06 | 3 | 5g_basics.md, runbook_coverage.md, escalation_policy.md, runbook_interference.md |
| rag-07 | 2 | 5g_basics.md, kpi_glossary.md, runbook_capacity_mobility.md, runbook_capacity_mobility.md |

## Data sanity check: runbook rules applied with the tool implementations

Checks that each planted root cause is detectable in the generated data (not an agent metric).

| Route | Expected | Detected | Pass | Evidence |
|---|---|---|---|---|
| R1 | healthy | none | yes | {"low_throughput_rows": 0, "avg_scheduled_rbs": 249.4} |
| R2 | RC2 | RC2 | yes | {"low_throughput_rows": 60, "avg_scheduled_rbs": 235.6, "distance_km_pci_307": 1.574, "avg_speed_low_rows_kmh": 19.7, "max_handovers_in_60s": 0} |
| R3 | RC6 | RC6 | yes | {"low_throughput_rows": 60, "avg_scheduled_rbs": 239.6, "distance_km_pci_205": 0.447, "pci_mod30_conflict": [205, 145], "avg_speed_low_rows_kmh": 14.9, "max_handovers_in_60s": 0} |
| R4 | RC8 | RC8 | yes | {"low_throughput_rows": 60, "avg_scheduled_rbs": 113.0, "distance_km_pci_102": 0.363, "avg_speed_low_rows_kmh": 9.9, "max_handovers_in_60s": 0} |
| R5 | RC7 | RC7 | yes | {"low_throughput_rows": 50, "avg_scheduled_rbs": 223.1, "distance_km_pci_204": 0.203, "avg_speed_low_rows_kmh": 70.9, "max_handovers_in_60s": 0} |
| R6 | RC5 | RC5 | yes | {"low_throughput_rows": 10, "avg_scheduled_rbs": 222.6, "distance_km_pci_101": 0.411, "distance_km_pci_102": 0.436, "avg_speed_low_rows_kmh": 15.9, "max_handovers_in_60s": 5} |

Overall: PASS
