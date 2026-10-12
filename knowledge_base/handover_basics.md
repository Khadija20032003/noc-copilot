# Handover basics in 5G NR

This document explains what a handover is in 5G New Radio (NR), how measurement events A3 and A5 trigger it, and how handover settings prevent ping-pong. It also explains how handover problems (too late, too early, too frequent) link to NordTel root causes RC3, RC5 and RC7.

## What a handover is and why it exists

A handover is the procedure that moves a connected user equipment (UE) from one cell (the serving cell) to another cell (the target cell) without dropping the connection. Handovers exist because a UE moves and radio conditions change: the serving cell signal gets weaker while a neighbor cell gets stronger. Without a handover, the UE would stay on a weak cell, its downlink (DL) throughput would fall, and the connection could drop.

In 5G NR, the network decides the handover (except conditional handover, where the network prepares it and the UE executes it). The UE measures the serving cell and neighbor cells and sends measurement reports to the base station (gNB). The gNB then prepares the target cell and sends the handover command to the UE.

## Measurement reports and handover events A3 and A5

The gNB configures the UE with measurement events. When the condition of an event is fulfilled, the UE sends a measurement report. Measurements are usually based on the Synchronization Signal Reference Signal Received Power (SS-RSRP) or on SS-RSRQ (Synchronization Signal Reference Signal Received Quality).

- **Event A3**: a neighbor cell becomes better than the serving cell by an offset. Example: with an offset of 3 dB, the UE reports when the neighbor SS-RSRP is more than 3 dB above the serving SS-RSRP. A3 is the most common trigger for intra-frequency handovers.
- **Event A5**: the serving cell becomes worse than threshold1 AND a neighbor cell becomes better than threshold2. Example: serving SS-RSRP below -105 dBm and neighbor SS-RSRP above -100 dBm. A5 is often used for inter-frequency handovers or to move the UE only once the serving cell is really weak.

## Hysteresis, offset and time-to-trigger (TTT)

Three handover parameters protect against unnecessary handovers caused by short signal fluctuations (fading):

- **Offset**: how much better the neighbor must be than the serving cell (event A3). A larger offset makes handovers later and rarer.
- **Hysteresis**: an extra margin, in dB, that the signals must cross both to enter the event condition and to leave it. It stops the condition from switching on and off when the two signals are almost equal.
- **Time-to-trigger (TTT)**: how long the event condition must stay true before the UE sends the report, for example a few hundred milliseconds. A short spike in neighbor signal does not trigger a handover.

Together, offset, hysteresis and TTT reduce ping-pong. If they are too large, handovers become too late. If they are too small, handovers become too early and too frequent.

## Frequent handovers and ping-pong

NordTel definitions:

- **Frequent handovers**: 3 or more handovers within 60 seconds for the same UE.
- **Ping-pong**: the UE hands over to a new cell and returns to the previous cell within 5 seconds.

Each handover interrupts data briefly and resets some link adaptation, so many handovers reduce average DL throughput. Frequent handovers map to root cause **RC5 Frequent handovers degrade performance**. In the `measurements` table, a change of `serving_pci` (Physical Cell Identity) between consecutive `timestamp` rows indicates a handover. Count these changes over a sliding 60 second window (any 60 seconds, not fixed blocks) with `query_network_data` to detect frequent handovers and ping-pong. PCIs are reused, so join `measurements` to `cells` on PCI within the test area, taking the nearest cell with that PCI.

## How UE speed interacts with handovers

A fast UE (for example on a highway or a train) crosses cell borders quickly, so it needs more handovers per minute. With a long TTT, a fast UE may already be deep inside the new cell before the handover happens, so it spends time on a weak serving cell. The radio channel also changes faster: channel quality reports (CQI, Channel Quality Indicator) and beam choices become outdated quickly, which makes link adaptation harder. The Doppler shift itself is small (about 130 Hz at 40 km/h on 3.5 GHz, compared with the 30 kHz subcarrier spacing).

A UE speed above 40 km/h maps to root cause **RC7 High UE speed (above 40 km/h)**. RC7 is a test condition, not a network fault: it is P3 Minor (annotate and re-test), see escalation_policy.md. Check `ue_speed_kmh` in the `measurements` table. When high speed and frequent handovers appear together, check the timing: if the frequent handovers happen during the high-speed rows, speed may be the driver.

## Handover too late vs too early

**Too late handover**: the offset, hysteresis or TTT is too large, or a neighbor relation is missing. The UE stays on a weak serving cell while a neighbor is clearly stronger. Typical evidence: poor serving SS-RSRP or SS-SINR (Signal to Interference plus Noise Ratio), and neighbor RSRP clearly above the serving RSRP for longer than the TTT; in severe cases a radio link failure (call drop) before the handover completes. This maps to root cause **RC3 Better neighbor available**: a neighbor cell would provide higher throughput. Do not confuse it with RC4 Overlapping coverage, where several non-colocated co-frequency cells at similar levels overlap so no cell dominates and SINR is poor.

**Too early handover**: the offset, hysteresis or TTT is too small. The UE moves to a neighbor that is only briefly stronger, then returns. Typical evidence: ping-pong (return to the previous cell within 5 seconds) and 3 or more handovers within 60 seconds. This maps to root cause **RC5 Frequent handovers degrade performance**.

Handover parameter changes are recommendations only. The assistant never changes the network; it opens a ticket with `create_ticket` for the RAN (Radio Access Network) optimization team.

## Related documents

- 5g_basics.md
- kpi_glossary.md
- runbook_low_throughput.md
- runbook_coverage.md
- runbook_interference.md
- runbook_capacity_mobility.md
- escalation_policy.md
