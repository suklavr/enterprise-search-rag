---
id: faq-losses-differ-between-runs
title: Why do losses differ slightly between two runs with the same settings?
collection: faqs
url: internal://faqs/losses-differ-between-runs
tags: [analysis, random, seed]
fictional: true
---
# Why do losses differ slightly between two runs with the same settings?
The simulation uses random draws for frequency, footprint, impact and severity. Two runs with the same settings converge at the portfolio level but individual occurrences differ. For exact reproducibility export the YLT of one run rather than re-running.
