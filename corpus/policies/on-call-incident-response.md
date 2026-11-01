---
id: pol-on-call-incident-response
title: On-call and incident response
collection: policies
url: internal://policies/on-call-incident-response
tags: [on-call, incident, severity, postmortem, pagerduty]
fictional: true
---
# On-call rotation
Every production service has a primary and a secondary on-call engineer on a weekly rotation. On-call engineers acknowledge a page within 15 minutes and may hand over to the secondary if unavailable. Time on call outside working hours is compensated per the local employment agreement.

# Incident severities
Severity 1: the platform is down or client data is at risk; all hands, status page updated within 30 minutes. Severity 2: a major feature is unusable for many clients; fix within the working day. Severity 3: degraded or single-client impact; fix within five working days. Severity 4: cosmetic; backlog.

# Communication
Incidents are run in a dedicated chat channel with an incident commander. Client-facing updates go through the support team, never directly from engineers.

# Postmortems
Every Severity 1 and 2 incident gets a blameless postmortem within five working days, with action items tracked in Jira until closed.
