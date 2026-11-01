---
id: doc-footprint-module
title: Footprint module
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/footprint-module?root=599
tags: [footprint, dfp, afp, hfp, nfp]
fictional: false
---
# Deciding who is affected
The footprint module decides which companies in the portfolio are affected by an occurrence of a scenario on a selected SPoF. It tries four footprint types in priority order.

# Detailed footprint (DFP)
The detailed footprint is a list of companies known to depend on the SPoF. It relies on matching the insured company to CyberCube's company database by name or website (the EIL match). A company in the DFP for the SPoF is affected according to the confidence of that record.

# Hybrid footprint (HFP)
The hybrid footprint applies only to regional cloud service provider events, scenarios 36 to 40. When a regional SPoF is selected and the company is not in that regional DFP, the model checks the global parent SPoF's detailed footprint and scales the market share by the region.

# Negative footprint (NFP)
The negative footprint check removes companies that have enough alternative SPoFs to be unaffected by the outage of this one.

# Aggregate footprint (AFP)
Companies not covered by the previous steps are selected probabilistically from the SPoF's market share, adjusted by industry adoption, company size and regional reliance factors. Companies affected through the aggregate footprint use the default Importance of Dependency tier 2 in the severity module.

# Footprint counts in reports
The By Portfolio (Detailed) report shows DFP, HFP, AFP, Footprint, Impact and Claim counts for every occurrence, so an unexpectedly large event can be traced to the footprint type that produced it.
