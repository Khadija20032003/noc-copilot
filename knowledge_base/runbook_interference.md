# Runbook: interference problems (RC4, RC6)

This document explains how to troubleshoot low downlink throughput caused by interference in NordTel 5G NR (New Radio) cells. It covers RC4 Overlapping coverage and RC6 PCI (Physical Cell Identity) mod 30 conflict between serving and neighbor cell causes interference, and how to tell them apart.

## Why interference lowers throughput

In 5G NR, interference has a typical signature, written "Good or Fair RSRP with poor SINR": SS-RSRP (Synchronization Signal Reference Signal Received Power) is Good or Fair (-105 dBm or better), but SS-SINR (Signal to Interference plus Noise Ratio) is Poor (below 0 dB) or low Fair (0 to 5 dB). The serving signal is strong enough, but another signal on the same frequency is almost as strong. With low SINR, the gNB (5G base station) selects a lower MCS (Modulation and Coding Scheme) and fewer MIMO (Multiple Input Multiple Output) layers, so downlink (DL) throughput falls below the NordTel target of 600 Mbps. Raising the serving cell's power rarely fixes SINR on its own: it also raises interference to neighbor cells.

## RC4 Overlapping coverage

### Symptoms
- Good or Fair RSRP with poor SINR, low DL throughput.
- A neighbor cell on another site (non-colocated) and on the same frequency (co-frequency) is strong: `neighbor_rsrp_dbm` within 3 dB of `ss_rsrp_dbm`, or higher.
- RC4 vs RC3: in RC4 Overlapping coverage, several (two or more) non-colocated co-frequency cells at similar levels overlap so no cell dominates and SINR is poor. If instead one neighbor is clearly stronger and the UE (user equipment) should have handed over, it is RC3 Better neighbor available.

### How to confirm
1. With `query_network_data`, read `ss_rsrp_dbm`, `ss_sinr_db`, `neighbor_pci` and `neighbor_rsrp_dbm` from table `measurements`.
2. Apply the 3 dB rule (strong if `neighbor_rsrp_dbm` >= `ss_rsrp_dbm` minus 3 dB) and count distinct strong `neighbor_pci` values over the period: two or more means no dominant cell.
3. In table `cells`, compare `frequency_mhz` of the serving and neighbor PCI. Equal values mean co-frequency. PCIs are reused, so join on PCI within the test area and take the nearest cell with that PCI.
4. Compare `site_name`, or use `network_calculator` (distance) between the two cells. Different sites mean non-colocated.
5. Use `network_calculator` (PCI mod 30 check). If the values differ, RC6 is ruled out and RC4 is the main suspect if step 2 found two or more strong neighbors.

### Likely causes
- Too little downtilt on one or both cells, so their footprints overlap.
- Azimuths (`azimuth_deg`) pointing toward each other.
- Dense site grid where no single cell dominates.

### Recommended actions
- Recommend a downtilt increase of 1 to 2 degrees on the cell that reaches too far.
- Recommend an azimuth change to reduce the overlap area.
- Re-check SINR on the route after each change. Avoid creating coverage holes (see RC1 Downtilt too large in runbook_coverage.md).

### When to escalate
- Tilt and azimuth changes for RC4 Overlapping coverage need approval by the RAN (Radio Access Network) optimization team. Open a ticket with `create_ticket` (P2 if any cell stays below 600 Mbps for more than 30 min, or if it shows a Poor KPI (Key Performance Indicator) on a busy cell; otherwise P3). A busy cell is one the NOC (Network Operations Center) dashboard flags as high traffic; the engineer confirms it.

## RC6 PCI mod 30 conflict between serving and neighbor cell causes interference

### Why PCI mod 30 matters
In 5G NR, PCI mod 30 sets the default sequence group of uplink reference signals: the PUCCH (Physical Uplink Control Channel) DMRS (Demodulation Reference Signal) and the PUSCH (Physical Uplink Shared Channel) DMRS when transform precoding is used, unless a separate ID is configured. When two overlapping co-frequency cells have the same PCI mod 30, these uplink signals use the same group and are harder to separate, so the gNB uplink channel estimation degrades. The PCI mod 30 match does not by itself lower the downlink SS-SINR: in drive-test data, the low DL SINR comes from the strong co-frequency neighbor, and the PCI mod 30 match is a planning error found next to it. PCI mod 3 is a separate, SSB-related (Synchronization Signal Block) planning check.

### Symptoms
- Good or Fair RSRP with poor SINR, low DL throughput.
- A strong co-frequency neighbor (within 3 dB of the serving cell, or higher) is present.

### How to confirm
1. With `query_network_data`, get `serving_pci` and `neighbor_pci` from table `measurements`.
2. Use `network_calculator` (PCI mod 30 check). Equal values mean a PCI mod 30 conflict.
3. In table `cells`, check that `frequency_mhz` is equal for both cells. A conflict only matters for co-frequency cells.
4. Apply the 3 dB rule to `neighbor_rsrp_dbm` and `ss_rsrp_dbm` to confirm the neighbor is strong.

### Likely causes
- PCI planning that did not consider PCI mod 30, or a new site added without re-planning.

### Recommended actions
- Recommend a PCI re-plan so strong co-frequency neighbors have different PCI mod 30 values (and different PCI mod 3 values).
- If overlap is also high, add tilt or azimuth changes as for RC4.

### When to escalate
- A PCI re-plan needs approval by the RAN optimization team. Open a ticket with `create_ticket` and list both PCIs and their PCI mod 30 values. Severity follows the same P2 or P3 rules as RC4 (usually P3; P4 if found only in a planning review).

## How to tell RC4 and RC6 apart

RC4 Overlapping coverage and RC6 PCI mod 30 conflict look alike: both show Good or Fair RSRP with poor SINR and a strong co-frequency neighbor. The deciding check is the `network_calculator` PCI mod 30 check. Equal values point to RC6. Different values, with two or more strong co-frequency neighbors on different sites, point to RC4. Both can be present together: recommend the PCI re-plan for the uplink, and the RC4 overlap actions for the poor downlink SINR.

## Related documents
- runbook_low_throughput.md
- runbook_coverage.md
- runbook_capacity_mobility.md
- kpi_glossary.md
- 5g_basics.md
- escalation_policy.md
