# NordTel escalation policy for 5G cell degradations

This document defines NordTel incident severities (P1 to P4), response times, team ownership and the content of an incident ticket. It also sets the rules the NOC (Network Operations Center) Copilot assistant must follow when it recommends actions and opens tickets.

## Incident severity levels and response times

NordTel uses four incident severity levels for 5G NR (New Radio) cell degradations:

| Severity | Definition | Response time |
|---|---|---|
| P1 Critical | Site down (always P1) or more than 3 cells degraded in one area, or emergency service impact. | 15 min |
| P2 Major | Two independent conditions: (a) any cell with DL (downlink) throughput below 600 Mbps for more than 30 min, OR (b) a Poor KPI (Key Performance Indicator) on a busy cell. | 1 hour |
| P3 Minor | Intermittent or single-route degradation with a known cause. | 1 business day |
| P4 Planning | Optimization suggestion, no customer impact. | Next planning cycle |

A KPI is "Poor" according to the NordTel thresholds: SS-RSRP (Synchronization Signal Reference Signal Received Power) < -105 dBm, SS-SINR (Signal to Interference plus Noise Ratio) < 0 dB, or SS-RSRQ (Synchronization Signal Reference Signal Received Quality) < -15 dB. A "busy cell" is a cell the NOC dashboard flags as high traffic. It cannot be derived from the `cells` and `measurements` tables, so the NOC on-shift engineer confirms it; the assistant must ask if it is unknown. A site down is always P1 Critical. RC7 High UE speed (above 40 km/h; UE is user equipment) is a test condition, not a network fault, so it is P3 Minor. When an incident matches two severity levels, use the higher one. Exception: RC7 High UE speed stays P3 Minor unless another root cause raises it (for example, a normal-speed re-test still shows throughput below 600 Mbps, which points to another root cause). Severity can be raised or lowered by the on-shift engineer as new evidence arrives.

## Who owns what

- **NOC on-shift engineer:** first owner of every incident. Reviews the assistant's diagnosis, confirms the severity, approves ticket creation and coordinates the other teams.
- **RAN (Radio Access Network) optimization team:** owns radio parameter and physical changes: downtilt, azimuth, PCI (Physical Cell Identity) re-plan, handover parameters, scheduler settings and load balancing. Also owns P4 planning items.
- **Field operations:** owns on-site work: hardware faults, power, antenna inspection, and applying approved physical changes at the site.
- **Vendor support:** owns equipment and software defects (for example a software bug or a hardware failure that field operations cannot fix). Engaged by the NOC on-shift engineer, usually for P1 and P2 incidents.

## Incident ticket content

Every NordTel incident ticket, whether opened by an engineer or through the `create_ticket` tool, must contain these fields:

- **severity:** P1, P2, P3 or P4.
- **affected PCI(s):** the serving PCI and any neighbor PCI involved.
- **site_name:** from table `cells`.
- **symptom:** short description, for example "DL throughput below 600 Mbps on test route".
- **evidence with KPI values:** measured values from table `measurements`, for example `dl_throughput_mbps`, `ss_rsrp_dbm`, `ss_sinr_db`, `scheduled_rbs`, with time range.
- **suspected root cause ID:** RC1 to RC8 (for example "RC8 Low scheduled resources"), or "unknown" with the missing data listed.
- **recommended action:** what the assistant or engineer suggests, and which team should act.
- **confidence:** high, medium or low, based on how clearly the data matches the root cause.

A ticket is incomplete, and should not be submitted, if it has no KPI evidence (or an explicit list of missing data) or no root cause field (RC1 to RC8, or "unknown").

## Rules for the NOC Copilot assistant

- The assistant **only recommends and opens tickets; it never changes the network.**
- The assistant opens a ticket with `create_ticket` **only after human confirmation** by the NOC on-shift engineer. It shows the draft ticket first.
- The assistant must show its evidence (KPI values and data checks) and state its confidence. If data is missing, it says so instead of guessing.
- The assistant must not mark an incident as resolved; the owning team does that.

## Changes that need RAN optimization approval

Physical changes need approval by the RAN optimization team before anyone applies them:

- Downtilt changes, electronic or mechanical (default electronic downtilt is 6 degrees; typical step is 1 to 2 degrees).
- Azimuth changes.
- PCI re-plan (for example to fix RC6 PCI mod 30 conflict between serving and neighbor cell causes interference).

The RAN optimization team should also review handover parameter changes, scheduler settings, bandwidth configuration and load balancing. The NOC on-shift engineer can open the ticket, but cannot approve these changes alone.

## Examples

These examples show how typical situations map to NordTel severity levels:

1. **Four cells degraded around one site cluster** after a power alarm, all with DL throughput far below 600 Mbps. More than 3 cells degraded in one area: **P1 Critical**, respond in 15 min, field operations engaged.
2. **One busy cell below 600 Mbps for 45 minutes**, with no radio KPI (RSRP, SINR, RSRQ) in the Poor band and average `scheduled_rbs` of 120 on a 100 MHz carrier during a full-buffer test (RC8 Low scheduled resources). Below 600 Mbps for more than 30 min: **P2 Major**, respond in 1 hour, RAN optimization team reviews load balancing.
3. **A single test route with low throughput** where `ue_speed_kmh` is above 40 km/h (RC7 High UE speed). Single-route degradation with a known cause: **P3 Minor**, annotate the result and re-test at normal speed. No RAN optimization escalation is needed.

## Related documents
- runbook_low_throughput.md
- runbook_coverage.md
- runbook_interference.md
- runbook_capacity_mobility.md
- kpi_glossary.md
- 5g_basics.md
