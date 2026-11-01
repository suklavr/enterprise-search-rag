---
id: pol-secure-development
title: Secure development standard
collection: policies
url: internal://policies/secure-development
tags: [secure development, code review, dependencies, secrets]
fictional: true
---
# Code review
Every change to a production repository is reviewed by someone other than the author. Reviewers check for input validation, authorisation, error handling and logging of sensitive data.

# Dependencies
Dependabot alerts are triaged weekly. Critical alerts are fixed within 7 days, high within 30 days. Pinned versions and a lock file are mandatory.

# Secrets
Secrets live in the secrets manager, never in code, configuration files or chat. A secret that is committed by mistake is rotated the same day even if the commit is removed.

# Testing and quality gates
Unit tests run on every pull request. Services keep coverage at or above 80 percent as reported by SonarCloud, and the quality gate must pass before merge.
