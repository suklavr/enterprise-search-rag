---
id: pol-retention-backups
title: Data retention and backups
collection: policies
url: internal://policies/retention-backups
tags: [retention, backups, restore, deletion]
fictional: true
---
# Retention periods
Client portfolios and analysis results are kept for the life of the contract plus 12 months, then deleted. Application logs are kept for 13 months. Financial records are kept for 7 years. Recruitment data for unsuccessful candidates is deleted after 6 months.

# Backups
Production databases are backed up daily with point-in-time recovery for 35 days. Backups are encrypted and stored in a second region. A restore test is run monthly and the result is recorded.

# Deletion requests
Client deletion requests are completed within 30 days and confirmed in writing. Deletion covers primary storage, backups beyond the retention window and analytics copies.
