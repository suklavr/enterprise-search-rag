---
id: doc-api
title: CyberConnect API for PM v6
collection: product-docs
url: https://docs.cybcube.com/pm-probabilistic-modeling-api-v6/pm-v6-ga-probabilistic-modeling-api-specification?root=615
tags: [api, cyberconnect, endpoints, import, export]
fictional: false
---
# Hosts and versions
PM v6 is served by the CyberConnect API at api.pm.cybcube.com with path version v3. The previous model, v5.5, used api.pmv5.cybcube.com with path version v2 and reached end of life in October 2025, extended where needed. Identifiers are GUIDs in v6; they were integers in v5.5.

# Core endpoints
Import a portfolio with POST /odap/import/v3/portfolios, or request a presigned URL for large files. Create analysis settings with /odap/platform/probabilistic/analyses/v3/settings and run an analysis with /odap/portfolios/probabilistic/v3/analyses. Export results from /odap/portfolios/probabilistic/analyses/export/v3/ followed by company, company-ylt, loss-metrics or sim-losses-detailed, then the portfolio ID and the analysis ID. Security scores export from /odap/portfolios/export/v3/security-scores/ followed by the portfolio ID.

# Analysis settings
Settings include the frequency distribution (for example POISSON), the severity distribution (for example LOGNORMAL) and fullCompanyYlt. Error codes are documented alongside the OpenAPI 3.0 specification.

# Release 6.30
PM v6.30, released in February 2026, added portfolio download endpoints at /odap/portfolios/export/v1/company-information/ with all, matched or unmatched, followed by the portfolio ID, to retrieve the company information behind a portfolio and its matching status.
