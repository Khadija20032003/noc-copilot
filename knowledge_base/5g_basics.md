# 5G NR Basics for NOC Engineers

This document introduces the core 5G New Radio (NR) concepts a junior NordTel engineer needs before diagnosing cell degradations. It covers network elements, Physical Cell Identity (PCI), frequency bands, bandwidth, antenna settings, the RAN (Radio Access Network) and core split, and the role of the NOC (Network Operations Center).

## What 5G NR is

5G New Radio (NR) is the radio interface of the fifth generation of mobile networks, standardized by 3GPP (3rd Generation Partnership Project). Compared with 4G LTE (Long Term Evolution), 5G NR supports wider channels, higher frequencies and flexible subcarrier spacing (15, 30, 60 or 120 kHz for data). At NordTel, 5G NR cells are monitored with SS-based measurements (measurements on the Synchronization Signal Block, SSB) such as SS-RSRP (Synchronization Signal Reference Signal Received Power) and SS-SINR (Signal to Interference plus Noise Ratio), which are explained in kpi_glossary.md.

## UE, gNodeB, cell, sector and site

- **UE (User Equipment)**: the user's device, for example a phone or a drive-test scanner.
- **gNodeB (gNB)**: the 5G base station. It schedules radio resources for the UEs it serves.
- **Cell**: one logical radio coverage area of a gNB on one carrier frequency. Each cell broadcasts its own PCI.
- **Sector**: the geographic slice covered by one antenna direction. A typical macro site has three sectors pointing roughly 120 degrees apart. One sector can carry several cells (one per frequency).
- **Site**: the physical location (tower or rooftop) with the gNB equipment and antennas. Cells on the same site are called colocated; cells on different sites are non-colocated.

In NordTel data, the table `cells` lists each cell with its pci, site_name, latitude, longitude, azimuth_deg, downtilt_deg, frequency_mhz and bandwidth_mhz.

## PCI and why PCI mod 30 matters

The Physical Cell Identity (PCI) is a number that lets a UE distinguish one 5G NR cell from another at the physical layer. 5G NR has **1008 PCI values, from 0 to 1007** (336 groups of 3). PCI values are reused across the network.

PCI mod 30 sets the default sequence group of uplink reference signals: the DMRS (Demodulation Reference Signal) of the PUCCH (Physical Uplink Control Channel), and of the PUSCH (Physical Uplink Shared Channel) when transform precoding is used, unless a separate ID is configured. When a serving cell and a strong co-frequency neighbor overlap and share the same **PCI mod 30** value, these uplink signals are harder to separate, which degrades uplink channel estimation. It does not by itself lower downlink SINR: in drive-test data, low downlink SINR comes from the strong co-frequency neighbor, and the PCI mod 30 match is a planning error found next to it. PCI mod 3 is a separate, SSB-related planning check. NordTel treats this as root cause **RC6 PCI mod 30 conflict between serving and neighbor cell causes interference**. The `network_calculator` tool can run the PCI mod 30 check. See runbook_interference.md.

## Frequency bands: FR1 and FR2

5G NR frequencies are split into two frequency ranges:

- **FR1 (Frequency Range 1, 410 MHz to 7.125 GHz, often called sub-6 GHz)**: it includes low bands (good coverage, lower capacity) and the **3.5 GHz mid-band, band n78**, which is the main 5G capacity layer in Europe.
- **FR2 (Frequency Range 2, millimeter wave)**: bands above 24 GHz. Very high capacity, but short range and poor wall penetration.

Higher frequencies lose more signal over distance, so a 3.5 GHz cell covers less area than a low-band cell.

## Bandwidth and why it affects throughput

Channel bandwidth is the width of spectrum a 5G NR cell uses, stored as bandwidth_mhz in the `cells` table. Throughput scales roughly with bandwidth: more spectrum means more resource blocks (RBs) that the gNB can schedule to UEs. A 100 MHz carrier with 30 kHz subcarrier spacing has 273 RBs. NordTel flags root cause **RC8 Low scheduled resources** with this rule: average scheduled RBs below **160** AND no radio KPI (Key Performance Indicator: RSRP, SINR or RSRQ, Reference Signal Received Quality) in the Poor band. The 160 RB rule assumes a 100 MHz carrier at 30 kHz subcarrier spacing; on narrower carriers, compare against the carrier maximum. Low RBs can also mean the test was not a full-buffer download (see kpi_glossary.md).

## Antenna azimuth and downtilt

- **Azimuth**: the horizontal direction the antenna points to, in degrees from north (0 is north, 90 is east). Stored as azimuth_deg.
- **Downtilt**: how much the antenna beam points down toward the ground, in degrees. Stored as downtilt_deg. NordTel default electronic downtilt is **6 degrees**, with typical adjustment steps of 1 to 2 degrees.
  - **Mechanical downtilt**: the antenna bracket is physically tilted. Changing it needs a site visit.
  - **Electrical (electronic) downtilt**: the beam is steered down inside the antenna, often remotely.

More downtilt shrinks the cell: too much gives weak far-end coverage (**RC1 Downtilt too large**). Too little lets the cell reach too far (**RC2 Overshooting**, coverage distance above 1 km). Any downtilt or azimuth change needs approval by the RAN optimization team.

## RAN vs 5G core

The **RAN (Radio Access Network)** is the gNBs, antennas and radio links, where most issues in this knowledge base occur. The **5G core (5GC)** connects users to services:

- **AMF (Access and Mobility Management Function)**: handles UE registration, connection and mobility signaling.
- **SMF (Session Management Function)**: sets up and manages data sessions and assigns Internet Protocol (IP) addresses.
- **UPF (User Plane Function)**: forwards user data packets between the RAN and the internet.

## What a NOC does

A NOC monitors the network around the clock. NOC engineers watch alarms and KPIs, diagnose degradations, open tickets with the right severity (P1 to P4) and escalate to expert teams. At NordTel, the NOC Copilot assistant searches this knowledge base, queries the `cells` and `measurements` tables and opens tickets. It never changes the network.

## Related documents

- kpi_glossary.md
- handover_basics.md
- runbook_low_throughput.md
- runbook_coverage.md
- runbook_interference.md
- runbook_capacity_mobility.md
- escalation_policy.md
