---
id: faq-api-ids-guid
title: My API calls fail with invalid portfolio id after moving to v6
collection: faqs
url: internal://faqs/api-ids-guid
tags: [api, migration]
fictional: true
---
# My API calls fail with invalid portfolio id after moving to v6
PM v6 identifiers are GUIDs; v5.5 used integers. Re-read the portfolio and analysis IDs from the v3 endpoints on api.pm.cybcube.com and do not reuse v2 integer IDs.
