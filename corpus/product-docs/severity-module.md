---
id: doc-severity-module
title: Severity module — cost components and modifiers
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/severity-modulelong?root=599
tags: [severity, cost components, modifiers, coverages]
fictional: false
---
# From calculated variables to coverages
The severity module computes the expected value and variance of each calculated variable, combines them linearly into cost components whose inclusion depends on the scenario, applies multiplicative modifiers, and sums cost components into coverages. The loss is then sampled from a lognormal distribution by default, with gamma or Pareto selectable, using the same random draw across the coverages of one company.

# Modifiers
The Large versus Non-large loss modifier marks 5 percent of events as large with a 4.0 multiplier and applies 0.85 to the rest. The Geography modifier uses the United States as the base of 1.0 with separate values for the UK, Germany, France, Japan and Other. The Security modifier is a composite of six control categories, GRC, IAM, NCM, VM, MD and IRR, normalised against peers and ranging from 0.5 to 2.0. For scenarios 36 to 44 only, an Importance of Dependency modifier with tiers 3, 2 and 1 applies, with aggregate-footprint companies defaulting to tier 2, together with a Severity-by-SPoF modifier. Missing data leaves a modifier at 1.0.

# Cost components and coverages
Cost components roll up to these coverages: Investigation and Response (notification, credit monitoring, detection and escalation), Extortion Payment (ransom), Data Restoration, Business Interruption (revenue loss and additional expenditure), Contingent Business Interruption (the same, from a third-party origin), Regulatory (HIPAA and PCI-DSS fines; Other fines is unused), Fund Transfer Fraud, and Legal Liability (legal fees, D&O, E&O, card replacement, PCI liability). Physical Damage and Intangible Loss exist as components but are not included in analyses. The engine's aggregate cost-component ID order used in reports is 1, 2, 9, 3, 10, 5, 4, 6.
