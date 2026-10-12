# Runbook: capacity and mobility issues (RC5, RC7, RC8)

This document covers three mobility and capacity root causes: RC5 Frequent handovers degrade performance, RC7 High UE speed (above 40 km/h), and RC8 Low scheduled resources (UE means user equipment).

## RC5 Frequent handovers degrade performance

**Symptoms.** For RC5 Frequent handovers, downlink (DL) throughput drops below the 600 Mbps target while the UE changes serving cell many times. Throughput dips at each handover.

**How to confirm.** Use `query_network_data` on table `measurements`, ordered by `timestamp`. Count changes of `serving_pci` (Physical Cell Identity) over a sliding 60 second window. RC5 is confirmed when there are **3 or more handovers within any 60 seconds**. Also flag ping-pong: a return to the previous `serving_pci` within **5 seconds**. Check `neighbor_rsrp_dbm` against `ss_rsrp_dbm` (SS-RSRP, Synchronization Signal Reference Signal Received Power): a neighbor within 3 dB (or higher) is a strong neighbor and often drives repeated handovers.

**Likely causes.**
- Cells with similar signal strength in one area, so no cell dominates.
- Handover parameters (offset, hysteresis, time-to-trigger) too small, so handovers trigger too early.
- RC4 Overlapping coverage, RC2 Overshooting or RC7 High UE speed (above 40 km/h).

**Recommended actions.**
- Identify the PCI pairs involved and check their `site_name`, `azimuth_deg` and `downtilt_deg` in table `cells`. PCIs are reused, so join on PCI within the test area and take the nearest cell with that PCI.
- Recommend a review of handover parameters (for example more hysteresis or a longer time-to-trigger) to reduce ping-pong.
- If one cell is overshooting or overlapping, recommend a downtilt adjustment of 1 to 2 degrees (default downtilt is 6 degrees).
- Any parameter or downtilt change needs RAN (Radio Access Network) optimization team approval.

**When to escalate.** Escalate RC5 Frequent handovers degrade performance to the RAN optimization team as P2 if any cell stays below 600 Mbps for more than 30 min or shows a Poor KPI (Key Performance Indicator) on a busy cell. A busy cell is one the NOC (Network Operations Center) dashboard flags as high traffic; the engineer confirms it. A single-route event with a known cause is P3; a pure tuning suggestion is P4.

## RC7 High UE speed (above 40 km/h)

**Symptoms.** For RC7 High UE speed, DL throughput drops and fluctuates quickly while the UE moves fast, for example on a highway or train. SS-SINR (Signal to Interference plus Noise Ratio) varies from sample to sample, and handovers are more frequent.

**How to confirm.** RC7 is confirmed when `ue_speed_kmh` (table `measurements`) is **above 40 km/h** during the low throughput samples. If throughput is good at low speed and poor at high speed on the same cell, speed is the main factor.

**Likely causes.**
- **Outdated channel reports:** fast fading (rapid signal variation from multipath) changes the channel within milliseconds, so channel quality reports (CQI, Channel Quality Indicator) and beam choices become outdated quickly, and the network picks less efficient modulation and fewer layers. Shadowing (slower variation from buildings and terrain) is a different effect.
- **Doppler shift is small:** at 40 km/h on 3.5 GHz the Doppler shift is about 130 Hz, small compared with the 30 kHz subcarrier spacing, so it is not the main problem.
- **More handovers:** a fast UE crosses cells quickly, so it spends more time in handovers (see RC5).

**Recommended actions.**
- RC7 High UE speed is a **test condition, not a network fault**. Annotate the result ("throughput reduced by high UE speed") and re-test at normal speed.
- Do not recommend physical changes (downtilt, azimuth) based only on high speed samples.
- For a real high-speed corridor (highway, railway), the RAN optimization team may plan mobility tuning as a P4 item.

**When to escalate.** Log RC7 High UE speed as P3 Minor (test condition, single-route degradation, known cause): annotate and re-test, with no RAN optimization escalation. Escalate only if throughput stays below 600 Mbps after a normal-speed re-test, which points to another root cause.

## RC8 Low scheduled resources (average scheduled RBs below 160)

**Symptoms.** For RC8 Low scheduled resources, DL throughput is below 600 Mbps even though no radio KPI (Key Performance Indicator: RSRP, SINR, RSRQ) is in the Poor band: SS-RSRP >= -105 dBm, SS-SINR (Signal to Interference plus Noise Ratio) >= 0 dB, SS-RSRQ (Synchronization Signal Reference Signal Received Quality) >= -15 dB. The UE receives a usable signal but is given too few resource blocks (RBs, also called PRBs, Physical Resource Blocks).

**How to confirm.** Use `query_network_data` to compute the average `scheduled_rbs` in table `measurements` for the serving PCI and period. RC8 is confirmed when average scheduled RBs are **below 160** AND no radio KPI (RSRP, SINR, RSRQ) is in the Poor band (classify with `network_calculator` and verify none is Poor). Check `bandwidth_mhz` in table `cells`: the 160 RB rule assumes a 100 MHz carrier at 30 kHz subcarrier spacing (273 RBs max); on narrower carriers, compare against the carrier maximum instead. Check the test type: without a full-buffer download, low RBs may just mean little data to send.

**Likely causes.**
- High cell load: many active users share the cell, so each UE gets fewer RBs.
- Scheduler configuration that limits resources per UE or favors other traffic.
- Cell bandwidth configured smaller than expected (low `bandwidth_mhz` means fewer RBs in total).
- Low traffic demand: not a full-buffer test, so the scheduler had little to send.

**Recommended actions.**
- If load is high, recommend load balancing toward a less loaded neighbor or another carrier.
- Recommend a scheduler settings review.
- If the cell is constantly loaded, raise a capacity planning item.

**When to escalate.** Escalate RC8 Low scheduled resources to the RAN optimization team as P2 if the cell stays below 600 Mbps for more than 30 minutes (the busy-cell Poor KPI clause cannot apply to RC8), P3 for an intermittent single-route event, or P4 for a capacity planning suggestion.

## Related documents
- runbook_low_throughput.md
- handover_basics.md
- kpi_glossary.md
- runbook_coverage.md
- runbook_interference.md
- escalation_policy.md
- 5g_basics.md
