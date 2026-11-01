---
id: doc-model-outputs
title: Model outputs: AAL, OEP, AEP, TCE and company year loss tables
collection: product-docs
url: https://docs.cybcube.com/model-outputs-v6/per-occurrence-exceedance-probability-oep-v6/oep-overview-v6?root=595
tags: [outputs, aal, oep, aep, tce, ylt, return period]
fictional: false
---
# Portfolio metrics
The model reports the Average Annual Loss (AAL), the standard deviation of annual loss (SD-AL) and the coefficient of variation (CV) of annual loss, plus three exceedance curves: the Aggregate Exceedance Probability (AEP) for total annual loss, the Occurrence Exceedance Probability (OEP) for the largest single occurrence in a year, and the Tail Conditional Expectation (TCE), the mean loss beyond a return period.

# What counts as one occurrence
The OEP groups rows by Occurrence ID, so a multi-OS malware event or a multi-region cloud outage that touches several rows is treated as a single occurrence rather than several smaller ones.

# Company-level year loss tables
Company-level YLTs report seven return periods: 20, 50, 100, 200, 250, 500 and 1,000 years, equivalent to exceedance probabilities from 5 percent down to 0.1 percent. For each return period the table takes a window of plus or minus ten simulations around the return-period loss. The footprint column is blank for attritional losses and otherwise says Detailed or Aggregate.
