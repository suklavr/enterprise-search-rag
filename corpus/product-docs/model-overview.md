---
id: doc-model-overview
title: Catastrophe Model v6 — overview and simulation pipeline
collection: product-docs
url: https://docs.cybcube.com/catastrophe-model-v6-model-overview/event-simulation-process?root=594
tags: [overview, pipeline, scenarios]
fictional: false
---
# What the model does
CyberCube's Catastrophe Model v6 (the Portfolio Manager model, often called PM v6) simulates cyber catastrophe losses for a portfolio of insured companies. Each simulation year draws catastrophe events, decides which companies in the portfolio are affected, sizes the loss for each affected company, and applies the policy terms to turn ground-up loss into insured loss.

# Simulation pipeline
The modules run in this order: Frequency, SPoF Selection, Severity Intensity, Footprint, Impact, Severity, Financial Loss. The order matters: the footprint decides who is hit before the impact and severity modules decide how badly, and policy terms are applied last.

# Simulation years
A probabilistic analysis runs up to 50,000 simulation years. The user interface offers 10,000 or 50,000 years; some documentation also mentions 25,000. More years give smoother tail metrics at the cost of run time.

# Scenario classes and event families
The v6 catalogue contains 33 scenario classes grouped into 10 event families, including 2D, 2M, 3CI, 3CS, 3N, 4CS, 4M, 4OS and 5OT. Scenario IDs in use are 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29 and 36 to 44. The 3CI family (scenarios 36 to 40) covers regional cloud service provider outages; scenarios 41 to 44 are the malware spread scenarios.
