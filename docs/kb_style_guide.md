# Knowledge base style guide

Project: "NOC Copilot", a multi-agent assistant that helps engineers at a fictional
mobile operator, **NordTel**, diagnose 5G cell degradations. These documents are the
RAG knowledge base. They are short, simple, and technically correct.

## Format rules
- Markdown, one H1 title, then H2 sections. 400 to 1000 words per document.
- First lines after the H1: a 1 to 2 sentence summary ("This document ...").
- Each H2 section must be self-contained (it will be retrieved as a chunk on its own):
  repeat the key term in the section instead of writing "as said above".
- Plain English for a junior engineer. Define each acronym the first time in each doc.
- No em dashes (the character U+2014) and no en dashes used as dashes. Use commas, colons
  or parentheses. Hyphens in words like "co-frequency" are fine.
- No invented 3GPP clause numbers. You may mention spec names generally
  (e.g. "defined by 3GPP in TS 38.215") only if certain they are correct.
- Runbooks use this structure: Symptoms, How to confirm (with data checks), Likely causes,
  Recommended actions, When to escalate.
- End every doc with a "## Related documents" section listing other file names.

## Shared facts (MUST be used identically in every doc, never contradict)

### KPI thresholds used by NordTel (5G NR, SS-based measurements)
| KPI | Good | Fair | Poor |
|---|---|---|---|
| SS-RSRP (dBm) | >= -90 | -90 to -105 | < -105 |
| SS-SINR (dB) | >= 13 | 0 to 13 | < 0 |
| SS-RSRQ (dB) | >= -10 | -10 to -15 | < -15 |

- Downlink (DL) throughput target on NordTel test routes: **600 Mbps**. Below 600 Mbps
  is a "low throughput" event.
- Average scheduled downlink resource blocks (RBs / PRBs): below **160** is considered too low.
- Overshooting: serving cell more than **1 km** from the user equipment (UE).
- High UE speed: above **40 km/h** degrades throughput.
- Frequent handovers: **3 or more handovers within 60 seconds**. Ping-pong: the UE returns to
  the previous cell within 5 seconds.
- PCI interference: serving and a strong neighbor cell share the same **PCI mod 30** value.
- Strong neighbor: neighbor RSRP within **3 dB** of the serving cell (or higher).
- Default electronic downtilt: **6 degrees**. Typical adjustment step: 1 to 2 degrees.

### The 8 root causes the system diagnoses (use these exact IDs and names)
- RC1 Downtilt too large: weak coverage at the far end of the cell.
- RC2 Overshooting: serving cell coverage distance exceeds 1 km.
- RC3 Better neighbor available: a neighbor cell would provide higher throughput.
- RC4 Overlapping coverage: non-colocated co-frequency neighbors overlap heavily.
- RC5 Frequent handovers degrade performance.
- RC6 PCI mod 30 conflict between serving and neighbor cell causes interference.
- RC7 High UE speed (above 40 km/h).
- RC8 Low scheduled resources: average scheduled RBs below 160.

### Data available to the assistant (refer to these names when describing checks)
- Table `cells`: pci, site_name, latitude, longitude, azimuth_deg, downtilt_deg, frequency_mhz, bandwidth_mhz
- Table `measurements`: timestamp, serving_pci, dl_throughput_mbps, ss_rsrp_dbm, ss_sinr_db,
  ss_rsrq_db, neighbor_pci, neighbor_rsrp_dbm, ue_speed_kmh, scheduled_rbs, latitude, longitude
- Tools: `search_knowledge_base`, `query_network_data`, `network_calculator` (distance, PCI mod 30
  check, threshold classification), `create_ticket`.

### NordTel incident severities
- P1 Critical: site down or more than 3 cells degraded in one area, or emergency service impact. Respond in 15 min.
- P2 Major: one cell with throughput below 600 Mbps for more than 30 min, or a poor KPI on a busy cell. Respond in 1 hour.
- P3 Minor: intermittent or single-route degradation with a known cause. Respond in 1 business day.
- P4 Planning: optimization suggestion, no customer impact. Next planning cycle.
- Physical changes (downtilt, azimuth, PCI re-plan) need approval by the RAN optimization team.
  The assistant only recommends and opens tickets; it never changes the network.

## File list (8 documents)
1. 5g_basics.md
2. kpi_glossary.md
3. handover_basics.md
4. runbook_low_throughput.md  (master triage runbook, points to the 3 specific runbooks)
5. runbook_coverage.md        (RC1, RC2, RC3)
6. runbook_interference.md    (RC4, RC6)
7. runbook_capacity_mobility.md (RC5, RC7, RC8)
8. escalation_policy.md

## Canonical rules (these override any earlier wording)
- **P2 rule** has two independent conditions: (a) ANY cell with DL throughput below 600 Mbps for more than 30 min, OR (b) a Poor KPI on a busy cell. "Busy cell" means a cell where the NOC dashboard flags high traffic; it cannot be derived from the two tables, so the engineer confirms it. Site down is ALWAYS P1.
- **RC7 (high UE speed)** is a test condition, not a network fault: classify as P3 Minor (annotate and re-test), consistent with escalation_policy.md.
- **RC8 radio condition**: average scheduled RBs below 160 AND no radio KPI (RSRP, SINR, RSRQ) in the Poor band. Use this exact wording everywhere. Caveats: the 160 RB rule assumes a 100 MHz carrier at 30 kHz subcarrier spacing (273 RBs max); on narrower carriers compare against the carrier maximum instead. Low RBs can also mean the test was not a full-buffer download (little data to send), so check the test type before blaming the network.
- **Interference signature** (RC4 and RC6): RSRP Good or Fair, SINR Poor or low Fair. Use "Good or Fair RSRP with poor SINR" everywhere.
- **PCI mod 30 (RC6)**: in 5G NR, PCI mod 30 sets the default sequence group of UPLINK reference signals (PUCCH and PUSCH DMRS when transform precoding is used, unless a separate ID is configured). Matching values between overlapping co-frequency cells make these uplink signals harder to separate and degrade uplink channel estimation. Do NOT mention SRS. Do NOT claim the mod 30 match by itself lowers downlink SINR; in drive-test data the low DL SINR comes from the strong co-frequency neighbor, and the PCI mod 30 match is a planning error found next to it. PCI mod 3 is a separate, SSB-related planning check.
- **Doppler (RC7)**: at 40 km/h on 3.5 GHz the Doppler shift is about 130 Hz, small compared with the 30 kHz subcarrier spacing. The main effects of speed are that channel quality reports (CQI) and beam choices become outdated quickly (fast fading changes the channel within milliseconds), and handovers become more frequent. Fast fading = rapid signal variation from multipath; shadowing = slower variation from buildings and terrain.
- **RC3 vs RC4**: both show a co-frequency neighbor within 3 dB. RC3 = the neighbor is clearly better (stronger, and the UE should have handed over: handover too late or missing neighbor relation); RC4 = several non-colocated co-frequency cells at similar levels overlap so no cell dominates and SINR is poor (overlap / dominance problem). Spelling: "non-colocated" and "colocated" (no hyphen).
- **Handover counting**: count serving_pci changes over a sliding 60 s window. PCIs are reused in the network, so join `measurements` to `cells` on PCI within the test area (nearest cell with that PCI).
- Define every acronym at first use in each doc (including RAN, PCI, MIMO, UE, SS-).
- Use the full root cause names from the list above at least once per doc where an RC is discussed.
