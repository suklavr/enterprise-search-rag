---
id: doc-severity-intensity-module
title: Severity intensity module
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/severity-intensity-module?root=599
tags: [severity, intensity, key variable]
fictional: false
---
# Three intensity levels
Each occurrence is assigned a severity intensity level: 1 Low with probability 60 percent, 2 Medium with 30 percent, or 3 High with 10 percent.

# How the level is drawn
Scenarios 6, 7, 9 and 37 draw the level directly from those probabilities. All other scenarios first draw a key variable from a scenario-specific distribution and map its percentile to the level: the 0 to 60th percentile is Low, 60 to 90 is Medium, and above 90 is High. Examples of key variables are a lognormal system downtime, a beta-distributed percentage of records stolen, a Weibull power restoration time for scenario 20, and a beta-distributed OS infection rate for scenarios 41 to 44.

# Where it shows up
The key variable is sampled once per occurrence and is shown in the year loss table output, so a very long outage or a very large breach can be traced back to the sampled value.
