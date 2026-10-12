# 5G NR KPI Glossary

This document defines the radio and performance KPIs (Key Performance Indicators) NordTel uses to diagnose 5G NR (New Radio) cell degradations, with NordTel thresholds, and how to map KPI patterns to root causes RC1 to RC8.

## NordTel KPI threshold table

NordTel measures radio KPIs on the SSB (Synchronization Signal Block), hence "SS-": SS-RSRP (Reference Signal Received Power, in dBm: decibels relative to one milliwatt), SS-SINR (Signal to Interference plus Noise Ratio) and SS-RSRQ (Reference Signal Received Quality). The `network_calculator` tool applies these thresholds.

| KPI | Good | Fair | Poor |
|---|---|---|---|
| SS-RSRP (dBm) | >= -90 | -90 to -105 | < -105 |
| SS-SINR (dB) | >= 13 | 0 to 13 | < 0 |
| SS-RSRQ (dB) | >= -10 | -10 to -15 | < -15 |

## SS-RSRP (signal strength)

SS-RSRP (Synchronization Signal Reference Signal Received Power) is the linear average power of the resource elements carrying the SSS (Secondary Synchronization Signal) of one cell's SSB, measured by the UE (User Equipment), as defined by 3GPP (3rd Generation Partnership Project) in TS 38.215. Unit: **dBm**. It shows coverage, independent of interference. NordTel SS-RSRP thresholds: Good >= -90 dBm, Fair -90 to -105 dBm, Poor < -105 dBm. Column: ss_rsrp_dbm in the `measurements` table. Neighbor strength is in neighbor_rsrp_dbm.

## SS-SINR (signal quality)

SS-SINR (Synchronization Signal to Interference plus Noise Ratio) compares the wanted SSB signal power with interference from other cells plus noise. Unit: **dB**. SINR drives the CQI (Channel Quality Indicator) the UE reports, which drives the MCS (Modulation and Coding Scheme) the base station chooses, so SS-SINR is closely linked to throughput. NordTel SS-SINR thresholds: Good >= 13 dB, Fair 0 to 13 dB, Poor < 0 dB; "poor SINR" in the interference signature means Poor or low Fair (0 to 5 dB). Column: ss_sinr_db.

## SS-RSRQ (received quality)

SS-RSRQ (Synchronization Signal Reference Signal Received Quality) is N x SS-RSRP divided by the NR carrier RSSI (Received Signal Strength Indicator), where N is the number of RBs (resource blocks) in the RSSI bandwidth (3GPP TS 38.215). Unit: **dB**, in practice negative. It drops with cell load or power from other cells. NordTel SS-RSRQ thresholds: Good >= -10 dB, Fair -10 to -15 dB, Poor < -15 dB. Column: ss_rsrq_db.

## DL throughput and the 600 Mbps target

DL (downlink) throughput is the user data rate from the network to the UE, in Mbps. Column: dl_throughput_mbps. The NordTel target on test routes is **600 Mbps**; any sample below it is a "low throughput" event. Throughput depends on radio quality (SINR), the number of scheduled resource blocks, and the number of MIMO (Multiple Input Multiple Output) layers.

## Resource blocks (PRBs) and the 160 RB rule

A resource block (RB or PRB, Physical Resource Block) is the unit of spectrum the gNB (5G base station) scheduler gives a UE: 12 consecutive subcarriers in frequency, allocated per slot. Column: scheduled_rbs. **RC8 Low scheduled resources** applies when average scheduled RBs are **below 160** AND no radio KPI (RSRP, SINR, RSRQ) is in the Poor band. Caveats: the 160 RB rule assumes a 100 MHz carrier at 30 kHz subcarrier spacing (273 RBs max); on narrower carriers (bandwidth_mhz in `cells`), compare against the carrier maximum instead. Low RBs can also mean the test was not a full-buffer download (little data to send), so check the test type.

## CQI and MCS

- **CQI (Channel Quality Indicator)**: a value from 0 to 15 that the UE reports to tell the gNB how good the channel is.
- **MCS (Modulation and Coding Scheme)**: the modulation, from QPSK (Quadrature Phase Shift Keying) up to 256QAM (256 Quadrature Amplitude Modulation), and the coding rate the gNB chooses, mainly based on CQI and HARQ (Hybrid Automatic Repeat Request) feedback. Higher MCS carries more bits per RB.

## Handover success rate, frequent handovers and ping-pong

Handover success rate is the percentage of handover attempts that succeed. NordTel flags **3 or more handovers within any sliding 60 second window** as frequent handovers (**RC5 Frequent handovers degrade performance**), and a return to the previous cell within 5 seconds as ping-pong.

## How to read KPIs together

No single KPI gives the root cause; read them together (PCI is the Physical Cell Identity):

| Pattern | Meaning | Candidate root causes |
|---|---|---|
| Good or Fair RSRP with poor SINR | Interference | RC4 Overlapping coverage, RC6 PCI mod 30 conflict between serving and neighbor cell causes interference |
| Fair or Poor SS-RSRP falling with distance, low SS-SINR | Weak coverage | RC1 Downtilt too large, RC2 Overshooting (serving cell more than 1 km away) |
| One co-frequency neighbor clearly stronger than the serving cell for a sustained period, no handover | Better cell exists (handover too late or missing neighbor relation) | RC3 Better neighbor available |
| Two or more distinct strong (within 3 dB) non-colocated co-frequency neighbor_pci values in the period, none dominant, poor SS-SINR | No dominant cell (overlap problem) | RC4 Overlapping coverage |
| No radio KPI in the Poor band, throughput below 600 Mbps | Radio acceptable; check resources, load, test type | RC8 Low scheduled resources (average scheduled_rbs below 160) |
| 3 or more serving_pci changes within 60 s | Mobility instability | RC5 Frequent handovers degrade performance |
| ue_speed_kmh above 40, KPIs fluctuating | Fast-moving UE (test condition, P3 Minor) | RC7 High UE speed (above 40 km/h) |

Useful checks: UE to serving cell distance, PCI mod 30 of serving_pci and neighbor_pci, and period averages of scheduled_rbs and ue_speed_kmh. Root causes can co-occur. PCIs are reused, so when joining `measurements` to `cells` on PCI, take the nearest cell with that PCI in the test area. A PCI mod 30 match is an uplink planning error; the poor SS-SINR comes from the strong co-frequency neighbor.

## Related documents

- 5g_basics.md
- handover_basics.md
- runbook_low_throughput.md
- runbook_coverage.md
- runbook_interference.md
- runbook_capacity_mobility.md
- escalation_policy.md
