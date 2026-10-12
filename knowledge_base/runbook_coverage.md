# Runbook: coverage problems (RC1, RC2, RC3)

This document explains how to troubleshoot low downlink throughput caused by coverage problems in NordTel 5G cells. It covers RC1 Downtilt too large, RC2 Overshooting and RC3 Better neighbor available.

## Why coverage problems lower throughput

In 5G NR (New Radio), a weak serving signal means a low SS-RSRP (Synchronization Signal Reference Signal Received Power). The SS-SINR (Signal to Interference plus Noise Ratio) then also drops, because noise and interference become large relative to the signal. The gNB (5G base station) then selects a lower MCS (Modulation and Coding Scheme). With fewer bits per resource block, downlink (DL) throughput falls below the 600 Mbps target. NordTel thresholds: SS-RSRP is poor below -105 dBm, SS-SINR is poor below 0 dB.

## RC1 Downtilt too large

### Symptoms
- Low DL throughput (below 600 Mbps) mainly at the far end of the cell.
- SS-RSRP fair or poor (below -90 dBm) at medium distance, while it is good close to the site.
- SS-SINR drops together with SS-RSRP as the user equipment (UE) moves away.

### How to confirm
1. With `query_network_data`, read `downtilt_deg` from table `cells` for the serving PCI (Physical Cell Identity). PCIs are reused, so take the nearest cell with that PCI in the test area.
2. A `downtilt_deg` above the NordTel default of 6 degrees supports RC1.
3. Use `network_calculator` (distance) between the cell and UE coordinates. Check that weak samples are at the far end, inside the expected cell range (less than 1 km; above 1 km, check RC2 Overshooting).
4. Use `network_calculator` (threshold classification) on `ss_rsrp_dbm` and `ss_sinr_db`.

### Likely causes
- The main beam lands short, so weak side lobes serve the cell edge.
- A previous anti-interference tilt change was too aggressive.

### Recommended actions
- Recommend an uptilt (reduce `downtilt_deg`) in steps of 1 to 2 degrees, then re-check RSRP and SINR on the route.
- Check that the uptilt does not create overshooting (RC2) or new overlap.

### When to escalate
- Any downtilt change needs approval by the RAN (Radio Access Network) optimization team. Open a ticket with `create_ticket`, usually P3. Use P2 if any cell stays below 600 Mbps for more than 30 min, or shows a Poor KPI (Key Performance Indicator) on a busy cell. A busy cell is one the NOC (Network Operations Center) dashboard flags as high traffic; the engineer confirms it.

## RC2 Overshooting

### Symptoms
- The serving cell is more than 1 km from the UE.
- SS-RSRP fair or poor and SS-SINR low, even though closer cells exist.
- Low DL throughput, sometimes with unexpected handovers.

### How to confirm
1. With `query_network_data`, get `serving_pci` from `measurements` and the cell position from `cells` (nearest cell with that PCI).
2. Use `network_calculator` (distance) between the cell and UE coordinates. A distance above 1 km confirms overshooting.
3. Check `downtilt_deg`: a value below the 6 degree default makes overshooting more likely. So does a high site (site height is not in the data; ask the RAN optimization team).
4. Check whether closer cells appear in `neighbor_pci`.

### Likely causes
- Downtilt too small, or the antenna on a high building or hill.
- Azimuth pointing over open terrain or water.
- A nearby cell is down or badly tilted, so the far cell takes the traffic.

### Recommended actions
- Recommend a downtilt increase in steps of 1 to 2 degrees on the overshooting cell.
- Review `azimuth_deg` if the beam points at an area served by other sites.
- Check closer cells are healthy before changing tilt.

### When to escalate
- Tilt or azimuth changes need RAN optimization team approval. Open a ticket with `create_ticket` for RC2 Overshooting (usually P3; P2 if a cell stays below 600 Mbps over 30 min or shows a Poor KPI on a busy cell). If a nearby site is down, that is always P1 Critical (respond in 15 min), see escalation_policy.md.

## RC3 Better neighbor available

### Symptoms
- The UE stays on a serving cell while a neighbor is stronger than the serving cell (`neighbor_rsrp_dbm` above `ss_rsrp_dbm`).
- Low DL throughput and low SS-SINR, because a strong co-frequency neighbor adds interference.

### How to confirm
1. With `query_network_data`, read `ss_rsrp_dbm`, `neighbor_pci` and `neighbor_rsrp_dbm` from table `measurements`.
2. Apply the NordTel 3 dB rule: the neighbor is strong if `neighbor_rsrp_dbm` >= `ss_rsrp_dbm` minus 3 dB.
3. Check the duration: a neighbor that stays stronger for longer than the time-to-trigger (TTT) without a handover points to RC3.
4. Use `network_calculator` (distance) to check whether the neighbor site is closer to the UE than the serving site.
5. Separate RC3 from RC4 Overlapping coverage. RC3 Better neighbor available: one neighbor is clearly stronger and the UE should have handed over (handover too late or missing neighbor relation). RC4: several non-colocated co-frequency cells overlap at similar levels (two or more distinct strong `neighbor_pci` values over the degraded period), so no cell dominates and SINR is poor; follow runbook_interference.md.

### Likely causes
- Missing neighbor relation, so the UE cannot hand over to the better cell.
- Handover parameters (offsets, hysteresis, time to trigger) too conservative.
- Unbalanced tilts, so the serving cell keeps the UE too long.

### Recommended actions
- Review the neighbor relation list and add the missing relation.
- Tune handover parameters toward the neighbor in small steps, to avoid RC5 Frequent handovers degrade performance (including ping-pong).
- If the imbalance comes from tilt, recommend 1 to 2 degree adjustments.

### When to escalate
- Any neighbor relation, handover parameter or tilt change needs RAN optimization team approval. Open a ticket with `create_ticket` for RC3 Better neighbor available (usually P3; P2 if any cell stays below 600 Mbps for more than 30 min, or shows a Poor KPI on a busy cell; P4 for pure tuning suggestions).

## Related documents
- runbook_low_throughput.md
- runbook_interference.md
- runbook_capacity_mobility.md
- handover_basics.md
- kpi_glossary.md
- 5g_basics.md
- escalation_policy.md
