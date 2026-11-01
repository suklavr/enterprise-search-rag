---
id: doc-reports
title: Working with reports in PM v6
collection: product-docs
url: https://docs.cybcube.com/pm-v6-working-with-reports/all-simulated-losses-reports-v6/simulated-losses-report?root=605
tags: [reports, simulated losses, loss metrics, by company, ylt, csv]
fictional: false
---
# Simulated losses reports
The simulated losses reports are By Portfolio, By Portfolio (Detailed), By Scenario, By Claim Count, By Company (AAL) and By Company YLT. The detailed report lists for every occurrence the Sample ID, Event Date, Family ID, Event ID, Event Occurrence ID, Target, Loss, the DFP, HFP, AFP, Footprint, Impact and Claim counts, Average Loss Size, eight coverage columns, the key assumption and its sampled value, sixteen contract-type columns and the Severity Intensity.

# Loss metrics report
The Loss Metrics report gives Gross, Net and Ceded figures. It is downloaded from the analysis page under Reports.

# By Company reports
The By Company reports require the Calculate Account Level Metrics option to be switched on when the analysis is run. The By Company YLT download is a zip of seven CSV files, one per return period, with the columns Sample ID, Event ID, Event Date, Target, Company, Contract ID, Footprint and Loss.

# Full company YLT
The full company year loss table is available through the API only, by setting fullCompanyYlt to true in the analysis settings. It is a zip containing one CSV with Sample Id, Event Id, Event Date, Target, Company, Contract Id, Footprint and Gross Loss. For a 100,000-policy portfolio it is roughly 0.5 GB and 5 million rows. A later change adds Family ID, Event Occurrence ID and eight coverage-loss columns to this file.
