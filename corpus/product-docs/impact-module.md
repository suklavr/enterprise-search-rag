---
id: doc-impact-module
title: Impact module (new in v6)
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/impact-module?root=599
tags: [impact, criticality, backups, patching]
fictional: false
---
# Purpose
The impact module is new in v6. After the footprint decides that a company is exposed to an occurrence, the impact module decides whether the exposure becomes a loss event for that company.

# Three event types
Cloud and outage scenarios use a reliance model, malware scenarios use a spread model, and breach and physical scenarios use a simplified model.

# Criticality
For cloud scenarios a criticality score is the weighted sum of coefficients for company Size, Industry, Backups, the Incident Response and Recovery score and the Governance, Risk and Compliance score, with firmographics and security posture each contributing half. The impact rate and its distribution give a criticality threshold, and a random draw against it decides impact.

# Malware spread
Malware scenarios 41 to 44 also use epicenter, penetration and spread parameters to model how far an infection travels.

# User inputs that matter
The v6 import adds three company-level fields that feed the impact module: Data Backups frequency, Patch Management and Network Segmentation. Companies with frequent backups, prompt patching and segmented networks are less likely to turn exposure into a loss.
