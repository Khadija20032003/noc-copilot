# Runbook: low downlink throughput (master triage)

This document is the master triage runbook for NordTel 5G cells with downlink (DL) throughput below 600 Mbps. It maps the data evidence to root causes RC1 to RC8 and points to the specific runbook.

## Low throughput symptoms

A low throughput event is any `measurements` row with `dl_throughput_mbps` below 600 on a NordTel test route. Typical symptoms:

- Low throughput on one cell (`serving_pci`) or one part of a route.
- Often, but not always, Poor radio KPIs (Key Performance Indicators) at the same time: SS-RSRP (Synchronization Signal Reference Signal Received Power) below -105 dBm, SS-SINR (Signal to Interference plus Noise Ratio) below 0 dB, or SS-RSRQ (Synchronization Signal Reference Signal Received Quality) below -15 dB.

## How to confirm low throughput (step-by-step triage)

Use `query_network_data` on `measurements` and `cells`, and `network_calculator` for distances, PCI (Physical Cell Identity) mod 30 checks and threshold classification.

1. **Isolate the low rows** (`dl_throughput_mbps` < 600): note the `timestamp` range and `serving_pci` values, and compare with good rows.
2. **Classify radio KPIs** (`ss_rsrp_dbm`, `ss_sinr_db`, `ss_rsrq_db`) as Good, Fair or Poor. Poor RSRP points to coverage. Good or Fair RSRP with poor SINR points to interference.
3. **Check distance to the serving cell.** Join UE (user equipment) positions in `measurements` with `cells` on `serving_pci` = `pci`. PCIs are reused, so take the nearest cell with that PCI in the test area. More than 1 km means overshooting.
4. **Check downtilt.** A `downtilt_deg` above the 6 degree default with weak RSRP at the far end of the cell suggests downtilt too large.
5. **Check the neighbor.** A `neighbor_rsrp_dbm` within 3 dB of `ss_rsrp_dbm`, or higher, is a strong neighbor. Run the PCI mod 30 check on `serving_pci` and `neighbor_pci`. In `cells`, same `frequency_mhz` and different `site_name` (non-colocated) means co-frequency overlap is possible.
6. **Check handovers.** Count `serving_pci` changes over a sliding 60 second window: 3 or more are frequent handovers; a return to the previous cell within 5 seconds is ping-pong.
7. **Check UE speed.** `ue_speed_kmh` above 40 km/h is high speed.
8. **Check scheduled resources.** Average `scheduled_rbs` below 160 AND no radio KPI (RSRP, SINR, RSRQ) in the Poor band means RC8 Low scheduled resources. Caveats: the 160 RB (resource block) rule assumes a 100 MHz carrier at 30 kHz subcarrier spacing (273 RBs max), so on narrower carriers compare against the carrier maximum; and a test that was not a full-buffer download also gives few RBs.

## Likely causes of low throughput (decision table)

| Observed evidence in low throughput rows | Root cause | Next runbook |
|---|---|---|
| Weak RSRP at far end of cell, `downtilt_deg` above the 6 degree default | RC1 Downtilt too large | runbook_coverage.md |
| UE more than 1 km from serving cell | RC2 Overshooting | runbook_coverage.md |
| One co-frequency neighbor clearly stronger than the serving cell for a sustained period, no handover | RC3 Better neighbor available | runbook_coverage.md |
| Two or more distinct strong `neighbor_pci` values (non-colocated, co-frequency), none dominant, Good or Fair RSRP with poor SINR | RC4 Overlapping coverage | runbook_interference.md |
| 3 or more handovers within any 60 seconds, or ping-pong within 5 seconds | RC5 Frequent handovers degrade performance | runbook_capacity_mobility.md |
| Strong co-frequency neighbor with the same PCI mod 30 value, Good or Fair RSRP with poor SINR | RC6 PCI mod 30 conflict between serving and neighbor cell causes interference | runbook_interference.md |
| `ue_speed_kmh` above 40 | RC7 High UE speed (above 40 km/h) | runbook_capacity_mobility.md |
| Average `scheduled_rbs` below 160 and no radio KPI (RSRP, SINR, RSRQ) in the Poor band | RC8 Low scheduled resources | runbook_capacity_mobility.md |

**RC3 vs RC4.** Both show a co-frequency neighbor within 3 dB. RC3 Better neighbor available: one neighbor is clearly stronger and the UE should have handed over (handover too late or missing neighbor relation). RC4 Overlapping coverage: two or more distinct strong `neighbor_pci` values (non-colocated, co-frequency) in the period, so no cell dominates and SINR is poor.

**RC6 note.** The poor SINR comes from the strong co-frequency neighbor; the PCI mod 30 match is an uplink planning error found next to it.

## Recommended actions when several low throughput causes appear together

To choose the main root cause:

- **Best explanation.** Prefer the cause present in most low rows and absent in good rows.
- **Timing.** A cause is credible only if it occurs at the same `timestamp` as the drop. High-speed rows that still have good throughput do not support RC7.
- **Chains.** Overshooting (RC2) can create a strong neighbor (RC3) or overlap (RC4); high speed (RC7) can create frequent handovers (RC5). Report the first cause as primary and the others as contributing.

The assistant only recommends and opens tickets with `create_ticket`. Physical changes (downtilt, azimuth, PCI re-plan) need approval by the RAN (Radio Access Network) optimization team.

## When to escalate low throughput

NordTel severities for low throughput (see escalation_policy.md):

- **P1 Critical** (respond in 15 min): site down (always P1), more than 3 cells degraded in one area, or emergency service impact.
- **P2 Major** (respond in 1 hour): (a) any cell with DL throughput below 600 Mbps for more than 30 min, OR (b) a Poor KPI on a busy cell. A busy cell is one the NOC (Network Operations Center) dashboard flags as high traffic; the engineer confirms it.
- **P3 Minor** (respond in 1 business day): intermittent or single-route degradation with a known cause. RC7 High UE speed is a test condition, so it is P3 Minor (annotate and re-test).
- **P4 Planning** (next planning cycle): optimization suggestion, no customer impact.

Escalate also when no root cause from RC1 to RC8 explains the low throughput rows, or when the data is missing (open the ticket with root cause "unknown" and list the missing data).

## Related documents

- kpi_glossary.md
- handover_basics.md
- runbook_coverage.md
- runbook_interference.md
- runbook_capacity_mobility.md
- escalation_policy.md
- 5g_basics.md
