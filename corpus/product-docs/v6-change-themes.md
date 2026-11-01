---
id: doc-v6-change-themes
title: What changed from v5.5 to v6
collection: product-docs
url: https://docs.cybcube.com/change-and-impact-v6/v6-catastrophe-model-change-document/summary?root=585
tags: [changes, v6, diversification, mitigation, regional cloud, malware]
fictional: false
---
# Two themes
The v6 changes fall under Diversification and Mitigation. There are no narrative changes to the scenarios themselves.

# Diversification: cloud and malware regionality
Regional cloud service provider SPoFs for scenarios 36 to 40 allow single-region, multi-region and global outages; multi-region outages use operating-system-style collision logic so the affected rows share one Event Occurrence ID. Malware scenarios 41 to 44 gain regionality through epicenter, penetration and spread parameters.

# Mitigation: impact module and security-driven severity
The new impact module and security-score-driven severity modifiers reward companies with stronger controls. Three new import fields feed this: Patch Management, Network Segmentation and Data Backup Frequency.

# Reading the change documents
The change-and-impact section has one page per module (frequency, SPoF selection, footprint, impact, severity intensity, severity, financial loss), a loss-changes page comparing v5.5 and v6 results, an EIL change document and an endpoint mapping from the PM v5.5 API to the v6 beta.
