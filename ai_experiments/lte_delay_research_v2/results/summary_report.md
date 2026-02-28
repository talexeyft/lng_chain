# LTE Packet Delay Counter Research Summary

**Counters Analyzed**: L.Traffic.DL.PktDelay.Time.QCI, L.Traffic.UL.PktDelay.Time.QCI, E-RAB.PktDelay.Avg

**Vendors Covered**: Huawei, Ericsson, Nokia, ZTE

**Standards Referenced**: TS_36_314, TS_28_552, TS_23_203

## Key Findings

- Packet delay counters measure time from PDCP SDU arrival to successful transmission
- All vendors include HARQ and RLC retransmissions in delay calculation
- Only successfully delivered packets are counted (discarded packets excluded)
- Typical GBR service delays: 20-80ms depending on QCI class
- Non-GBR browsing traffic typically experiences 50-200ms delay
