---
id: doc-frequency-module
title: Frequency module
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/frequency-module?root=599
tags: [frequency, rates]
fictional: false
---
# Three sources of event frequency
The frequency of each scenario class blends three components: a Historical component from observed events, an Expert Survey component from CyberCube's Cyber Threat Outlook Survey, and a Kill Chain component based on a modified Lockheed Martin kill chain with an added Post-Intrusion step. Each scenario has its own weights for the three components; for example Scenario 8 weights them 0.3, 0.1 and 0.6 for an overall annual rate of 0.1538.

# Conservative, default and aggressive rates
Users choose a conservative, default or aggressive frequency setting for an analysis. In the engine these map to separate rate tables for Negative Binomial and Poisson frequency distributions, with variants for the aggressive, conservative and default settings and for the expert survey, historical and threat-attack kill chain lambdas.

# Frequency distribution
The analysis settings include the frequency distribution, for example POISSON, which controls how many occurrences of a scenario are drawn per simulation year.
