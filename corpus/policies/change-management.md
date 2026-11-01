---
id: pol-change-management
title: Change management and deployments
collection: policies
url: internal://policies/change-management
tags: [change management, deployment, release, rollback]
fictional: true
---
# Standard changes
Code reaches production through the continuous delivery pipeline after a reviewed pull request, green tests and a passing quality gate. Standard changes need no separate approval.

# Significant changes
Database migrations that are not backwards compatible, infrastructure changes to networking or identity, and model version releases are significant changes. They need a written change plan with a rollback step, a named approver from the owning team and a deployment window outside client peak hours.

# Freeze periods
No significant changes in the last two working days before a quarter end or during an active Severity 1 incident, unless the change is the fix.

# Rollback
Every deployment must be reversible within 30 minutes. If a rollback is not possible, the change plan must say so and name the mitigation.
