---
id: doc-spof-selection-module
title: SPoF selection module
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/spof-selection-module?root=599
tags: [spof, single point of failure]
fictional: false
---
# One SPoF per occurrence
For every simulated occurrence the model selects one Single Point of Failure (SPoF) from the scenario's Modeled SPoF list. Together the modeled SPoFs for a scenario cover more than 90 percent of the relevant market share. SPoFs outside the list are Non-Modeled SPoFs and are not selected.

# How a SPoF is chosen
The likelihood of selecting a SPoF comes from its Security Score, its market share, and scenario-specific metrics such as cloud outage history for cloud scenarios or operating-system CVE history for OS scenarios. A SPoF with a larger footprint and a weaker security posture is more likely to be the target of an occurrence.
