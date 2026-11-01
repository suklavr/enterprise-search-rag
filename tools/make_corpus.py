"""Writes the demo corpus under corpus/.

- product-docs: articles written from CyberCube's PUBLIC documentation digest (docs.cybcube.com, v6 model). Facts only
  from that digest; every file links to its real section. Re-run after editing the texts below.
- policies and faqs: FICTIONAL sample content written for this demo. Every file says so in its front matter.

Usage: python tools/make_corpus.py [--out corpus]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

DOCS = "https://docs.cybcube.com"

PRODUCT_DOCS: list[tuple[str, str, str, list[str], str]] = [
    ("model-overview", "Catastrophe Model v6 — overview and simulation pipeline", f"{DOCS}/catastrophe-model-v6-model-overview/event-simulation-process?root=594", ["overview", "pipeline", "scenarios"], """
# What the model does
CyberCube's Catastrophe Model v6 (the Portfolio Manager model, often called PM v6) simulates cyber catastrophe losses for a portfolio of insured companies. Each simulation year draws catastrophe events, decides which companies in the portfolio are affected, sizes the loss for each affected company, and applies the policy terms to turn ground-up loss into insured loss.

# Simulation pipeline
The modules run in this order: Frequency, SPoF Selection, Severity Intensity, Footprint, Impact, Severity, Financial Loss. The order matters: the footprint decides who is hit before the impact and severity modules decide how badly, and policy terms are applied last.

# Simulation years
A probabilistic analysis runs up to 50,000 simulation years. The user interface offers 10,000 or 50,000 years; some documentation also mentions 25,000. More years give smoother tail metrics at the cost of run time.

# Scenario classes and event families
The v6 catalogue contains 33 scenario classes grouped into 10 event families, including 2D, 2M, 3CI, 3CS, 3N, 4CS, 4M, 4OS and 5OT. Scenario IDs in use are 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29 and 36 to 44. The 3CI family (scenarios 36 to 40) covers regional cloud service provider outages; scenarios 41 to 44 are the malware spread scenarios.
"""),
    ("frequency-module", "Frequency module", f"{DOCS}/event-modeling-v6/frequency-module?root=599", ["frequency", "rates"], """
# Three sources of event frequency
The frequency of each scenario class blends three components: a Historical component from observed events, an Expert Survey component from CyberCube's Cyber Threat Outlook Survey, and a Kill Chain component based on a modified Lockheed Martin kill chain with an added Post-Intrusion step. Each scenario has its own weights for the three components; for example Scenario 8 weights them 0.3, 0.1 and 0.6 for an overall annual rate of 0.1538.

# Conservative, default and aggressive rates
Users choose a conservative, default or aggressive frequency setting for an analysis. In the engine these map to separate rate tables for Negative Binomial and Poisson frequency distributions, with variants for the aggressive, conservative and default settings and for the expert survey, historical and threat-attack kill chain lambdas.

# Frequency distribution
The analysis settings include the frequency distribution, for example POISSON, which controls how many occurrences of a scenario are drawn per simulation year.
"""),
    ("spof-selection-module", "SPoF selection module", f"{DOCS}/event-modeling-v6/spof-selection-module?root=599", ["spof", "single point of failure"], """
# One SPoF per occurrence
For every simulated occurrence the model selects one Single Point of Failure (SPoF) from the scenario's Modeled SPoF list. Together the modeled SPoFs for a scenario cover more than 90 percent of the relevant market share. SPoFs outside the list are Non-Modeled SPoFs and are not selected.

# How a SPoF is chosen
The likelihood of selecting a SPoF comes from its Security Score, its market share, and scenario-specific metrics such as cloud outage history for cloud scenarios or operating-system CVE history for OS scenarios. A SPoF with a larger footprint and a weaker security posture is more likely to be the target of an occurrence.
"""),
    ("severity-intensity-module", "Severity intensity module", f"{DOCS}/event-modeling-v6/severity-intensity-module?root=599", ["severity", "intensity", "key variable"], """
# Three intensity levels
Each occurrence is assigned a severity intensity level: 1 Low with probability 60 percent, 2 Medium with 30 percent, or 3 High with 10 percent.

# How the level is drawn
Scenarios 6, 7, 9 and 37 draw the level directly from those probabilities. All other scenarios first draw a key variable from a scenario-specific distribution and map its percentile to the level: the 0 to 60th percentile is Low, 60 to 90 is Medium, and above 90 is High. Examples of key variables are a lognormal system downtime, a beta-distributed percentage of records stolen, a Weibull power restoration time for scenario 20, and a beta-distributed OS infection rate for scenarios 41 to 44.

# Where it shows up
The key variable is sampled once per occurrence and is shown in the year loss table output, so a very long outage or a very large breach can be traced back to the sampled value.
"""),
    ("footprint-module", "Footprint module", f"{DOCS}/event-modeling-v6/footprint-module?root=599", ["footprint", "dfp", "afp", "hfp", "nfp"], """
# Deciding who is affected
The footprint module decides which companies in the portfolio are affected by an occurrence of a scenario on a selected SPoF. It tries four footprint types in priority order.

# Detailed footprint (DFP)
The detailed footprint is a list of companies known to depend on the SPoF. It relies on matching the insured company to CyberCube's company database by name or website (the EIL match). A company in the DFP for the SPoF is affected according to the confidence of that record.

# Hybrid footprint (HFP)
The hybrid footprint applies only to regional cloud service provider events, scenarios 36 to 40. When a regional SPoF is selected and the company is not in that regional DFP, the model checks the global parent SPoF's detailed footprint and scales the market share by the region.

# Negative footprint (NFP)
The negative footprint check removes companies that have enough alternative SPoFs to be unaffected by the outage of this one.

# Aggregate footprint (AFP)
Companies not covered by the previous steps are selected probabilistically from the SPoF's market share, adjusted by industry adoption, company size and regional reliance factors. Companies affected through the aggregate footprint use the default Importance of Dependency tier 2 in the severity module.

# Footprint counts in reports
The By Portfolio (Detailed) report shows DFP, HFP, AFP, Footprint, Impact and Claim counts for every occurrence, so an unexpectedly large event can be traced to the footprint type that produced it.
"""),
    ("impact-module", "Impact module (new in v6)", f"{DOCS}/event-modeling-v6/impact-module?root=599", ["impact", "criticality", "backups", "patching"], """
# Purpose
The impact module is new in v6. After the footprint decides that a company is exposed to an occurrence, the impact module decides whether the exposure becomes a loss event for that company.

# Three event types
Cloud and outage scenarios use a reliance model, malware scenarios use a spread model, and breach and physical scenarios use a simplified model.

# Criticality
For cloud scenarios a criticality score is the weighted sum of coefficients for company Size, Industry, Backups, the Incident Response and Recovery score and the Governance, Risk and Compliance score, with firmographics and security posture each contributing half. The impact rate and its distribution give a criticality threshold, and a random draw against it decides impact.

# Malware spread
Malware scenarios 41 to 44 also use epicenter, penetration and spread parameters to model how far an infection travels.

# User inputs that matter
The v6 import adds three company-level fields that feed the impact module: Data Backups frequency, Patch Management and Network Segmentation. Companies with frequent backups, prompt patching and segmented networks are less likely to turn exposure into a loss.
"""),
    ("severity-module", "Severity module — cost components and modifiers", f"{DOCS}/event-modeling-v6/severity-modulelong?root=599", ["severity", "cost components", "modifiers", "coverages"], """
# From calculated variables to coverages
The severity module computes the expected value and variance of each calculated variable, combines them linearly into cost components whose inclusion depends on the scenario, applies multiplicative modifiers, and sums cost components into coverages. The loss is then sampled from a lognormal distribution by default, with gamma or Pareto selectable, using the same random draw across the coverages of one company.

# Modifiers
The Large versus Non-large loss modifier marks 5 percent of events as large with a 4.0 multiplier and applies 0.85 to the rest. The Geography modifier uses the United States as the base of 1.0 with separate values for the UK, Germany, France, Japan and Other. The Security modifier is a composite of six control categories, GRC, IAM, NCM, VM, MD and IRR, normalised against peers and ranging from 0.5 to 2.0. For scenarios 36 to 44 only, an Importance of Dependency modifier with tiers 3, 2 and 1 applies, with aggregate-footprint companies defaulting to tier 2, together with a Severity-by-SPoF modifier. Missing data leaves a modifier at 1.0.

# Cost components and coverages
Cost components roll up to these coverages: Investigation and Response (notification, credit monitoring, detection and escalation), Extortion Payment (ransom), Data Restoration, Business Interruption (revenue loss and additional expenditure), Contingent Business Interruption (the same, from a third-party origin), Regulatory (HIPAA and PCI-DSS fines; Other fines is unused), Fund Transfer Fraud, and Legal Liability (legal fees, D&O, E&O, card replacement, PCI liability). Physical Damage and Intangible Loss exist as components but are not included in analyses. The engine's aggregate cost-component ID order used in reports is 1, 2, 9, 3, 10, 5, 4, 6.
"""),
    ("financial-loss-module", "Financial loss module and reinsurance", f"{DOCS}/event-modeling-v6/financial-loss-module?root=599", ["financial loss", "deductible", "limit", "reinsurance", "quota share", "xol"], """
# Applying policy terms
Ground-up loss becomes insured loss in a fixed order: coverage-level deductibles and sublimits first (expressed in currency, as a percentage, or as hours for the business-interruption waiting period), then the policy attachment, then the occurrence deductible and limit, then the annual aggregate limit when the same company is hit more than once in a simulation year, and finally the participation percentage.

# Non-affirmative cover
Contract types other than Standalone and Other are treated as non-affirmative, and their losses are a probabilistic payout rather than a certain one.

# Reinsurance treaties
Two treaty types are supported. Quota Share takes a ceded percentage with an optional annual treaty limit. Risk Excess of Loss takes an attachment, a limit, a layer ceded percentage and an optional annual treaty limit; in years where the treaty limit is exceeded, all companies are scaled down equally. Treaties are assigned to policies through the Treaty Tag column, which accepts several tags separated by semicolons. Treaty stacking lets a quota share sit on top of an excess-of-loss layer.
"""),
    ("model-outputs", "Model outputs: AAL, OEP, AEP, TCE and company year loss tables", f"{DOCS}/model-outputs-v6/per-occurrence-exceedance-probability-oep-v6/oep-overview-v6?root=595", ["outputs", "aal", "oep", "aep", "tce", "ylt", "return period"], """
# Portfolio metrics
The model reports the Average Annual Loss (AAL), the standard deviation of annual loss (SD-AL) and the coefficient of variation (CV) of annual loss, plus three exceedance curves: the Aggregate Exceedance Probability (AEP) for total annual loss, the Occurrence Exceedance Probability (OEP) for the largest single occurrence in a year, and the Tail Conditional Expectation (TCE), the mean loss beyond a return period.

# What counts as one occurrence
The OEP groups rows by Occurrence ID, so a multi-OS malware event or a multi-region cloud outage that touches several rows is treated as a single occurrence rather than several smaller ones.

# Company-level year loss tables
Company-level YLTs report seven return periods: 20, 50, 100, 200, 250, 500 and 1,000 years, equivalent to exceedance probabilities from 5 percent down to 0.1 percent. For each return period the table takes a window of plus or minus ten simulations around the return-period loss. The footprint column is blank for attritional losses and otherwise says Detailed or Aggregate.
"""),
    ("reports", "Working with reports in PM v6", f"{DOCS}/pm-v6-working-with-reports/all-simulated-losses-reports-v6/simulated-losses-report?root=605", ["reports", "simulated losses", "loss metrics", "by company", "ylt", "csv"], """
# Simulated losses reports
The simulated losses reports are By Portfolio, By Portfolio (Detailed), By Scenario, By Claim Count, By Company (AAL) and By Company YLT. The detailed report lists for every occurrence the Sample ID, Event Date, Family ID, Event ID, Event Occurrence ID, Target, Loss, the DFP, HFP, AFP, Footprint, Impact and Claim counts, Average Loss Size, eight coverage columns, the key assumption and its sampled value, sixteen contract-type columns and the Severity Intensity.

# Loss metrics report
The Loss Metrics report gives Gross, Net and Ceded figures. It is downloaded from the analysis page under Reports.

# By Company reports
The By Company reports require the Calculate Account Level Metrics option to be switched on when the analysis is run. The By Company YLT download is a zip of seven CSV files, one per return period, with the columns Sample ID, Event ID, Event Date, Target, Company, Contract ID, Footprint and Loss.

# Full company YLT
The full company year loss table is available through the API only, by setting fullCompanyYlt to true in the analysis settings. It is a zip containing one CSV with Sample Id, Event Id, Event Date, Target, Company, Contract Id, Footprint and Gross Loss. For a 100,000-policy portfolio it is roughly 0.5 GB and 5 million rows. A later change adds Family ID, Event Occurrence ID and eight coverage-loss columns to this file.
"""),
    ("api", "CyberConnect API for PM v6", f"{DOCS}/pm-probabilistic-modeling-api-v6/pm-v6-ga-probabilistic-modeling-api-specification?root=615", ["api", "cyberconnect", "endpoints", "import", "export"], """
# Hosts and versions
PM v6 is served by the CyberConnect API at api.pm.cybcube.com with path version v3. The previous model, v5.5, used api.pmv5.cybcube.com with path version v2 and reached end of life in October 2025, extended where needed. Identifiers are GUIDs in v6; they were integers in v5.5.

# Core endpoints
Import a portfolio with POST /odap/import/v3/portfolios, or request a presigned URL for large files. Create analysis settings with /odap/platform/probabilistic/analyses/v3/settings and run an analysis with /odap/portfolios/probabilistic/v3/analyses. Export results from /odap/portfolios/probabilistic/analyses/export/v3/ followed by company, company-ylt, loss-metrics or sim-losses-detailed, then the portfolio ID and the analysis ID. Security scores export from /odap/portfolios/export/v3/security-scores/ followed by the portfolio ID.

# Analysis settings
Settings include the frequency distribution (for example POISSON), the severity distribution (for example LOGNORMAL) and fullCompanyYlt. Error codes are documented alongside the OpenAPI 3.0 specification.

# Release 6.30
PM v6.30, released in February 2026, added portfolio download endpoints at /odap/portfolios/export/v1/company-information/ with all, matched or unmatched, followed by the portfolio ID, to retrieve the company information behind a portfolio and its matching status.
"""),
    ("v6-change-themes", "What changed from v5.5 to v6", f"{DOCS}/change-and-impact-v6/v6-catastrophe-model-change-document/summary?root=585", ["changes", "v6", "diversification", "mitigation", "regional cloud", "malware"], """
# Two themes
The v6 changes fall under Diversification and Mitigation. There are no narrative changes to the scenarios themselves.

# Diversification: cloud and malware regionality
Regional cloud service provider SPoFs for scenarios 36 to 40 allow single-region, multi-region and global outages; multi-region outages use operating-system-style collision logic so the affected rows share one Event Occurrence ID. Malware scenarios 41 to 44 gain regionality through epicenter, penetration and spread parameters.

# Mitigation: impact module and security-driven severity
The new impact module and security-score-driven severity modifiers reward companies with stronger controls. Three new import fields feed this: Patch Management, Network Segmentation and Data Backup Frequency.

# Reading the change documents
The change-and-impact section has one page per module (frequency, SPoF selection, footprint, impact, severity intensity, severity, financial loss), a loss-changes page comparing v5.5 and v6 results, an EIL change document and an endpoint mapping from the PM v5.5 API to the v6 beta.
"""),
]

POLICIES: list[tuple[str, str, list[str], str]] = [
    ("acceptable-use", "Acceptable use of company systems", ["acceptable use", "laptops", "accounts"], """
# Scope
This policy applies to every employee, contractor and intern who uses company-issued devices, company accounts or company networks.

# Devices
Work is done on company-managed laptops. Personal laptops and phones may be used for email and chat only through the managed mobile apps, never for customer data, source code or production access. Devices must lock after five minutes of inactivity and run full-disk encryption.

# Accounts and credentials
Use single sign-on wherever it is offered. Never share an account or a password. Multi-factor authentication is mandatory for every system that supports it. Report a lost or stolen device to the security team within one hour.

# Prohibited use
Do not install software that bypasses endpoint protection, do not connect company devices to unknown networks without the VPN, and do not use company systems for cryptocurrency mining, file sharing of copyrighted material or any activity that would embarrass the company if it became public.
"""),
    ("information-security", "Information security policy", ["security", "cia", "controls", "mfa"], """
# Objectives
The company protects the confidentiality, integrity and availability of client exposure data, model data and internal information. Controls follow the six categories used in our own security scoring: governance risk and compliance, identity and access management, network and configuration management, vulnerability management, monitoring and detection, and incident response and recovery.

# Baseline controls
Multi-factor authentication on all accounts, least-privilege access reviewed quarterly, patching of critical vulnerabilities within 7 days and high within 30 days, centralised logging with 13 months of retention, and encrypted backups tested monthly.

# Responsibilities
The security team owns the policy and the tooling. Engineering managers own the controls inside their systems. Every employee completes security awareness training within 30 days of joining and annually after that.
"""),
    ("data-classification", "Data classification and handling", ["data classification", "confidential", "pii", "client data"], """
# Four classes
Public: already released, for example product documentation. Internal: business information not for release, for example roadmaps. Confidential: client portfolios, exposure data, contracts and personal data. Restricted: credentials, encryption keys and security findings.

# Handling rules
Confidential and Restricted data stay inside approved systems and are never pasted into personal tools, consumer AI services or unmanaged file shares. Client exposure data is stored only in the regions agreed in the client's contract. Personal data follows the data protection policy and is deleted or anonymised when no longer needed.

# Labelling and sharing
Documents carry their class in the footer. Sharing outside the company requires a signed agreement and the data owner's approval. Screenshots of client data in tickets or chat must be redacted.
"""),
    ("access-requests-offboarding", "Access requests, reviews and offboarding", ["access", "provisioning", "offboarding", "jira"], """
# Requesting access
Access to production systems, client data, cloud consoles and source control is requested through the IT service desk with the manager's approval. Requests state the system, the role and the business reason. Temporary access expires automatically after 30 days unless renewed.

# Reviews
System owners review access lists every quarter and remove anything no longer justified. Privileged access, such as cloud administrator roles and database write access, is reviewed monthly.

# Offboarding
On an employee's last day, HR triggers deprovisioning. Single sign-on is disabled within one hour, devices are returned and wiped, and shared credentials the person knew are rotated within five working days.
"""),
    ("on-call-incident-response", "On-call and incident response", ["on-call", "incident", "severity", "postmortem", "pagerduty"], """
# On-call rotation
Every production service has a primary and a secondary on-call engineer on a weekly rotation. On-call engineers acknowledge a page within 15 minutes and may hand over to the secondary if unavailable. Time on call outside working hours is compensated per the local employment agreement.

# Incident severities
Severity 1: the platform is down or client data is at risk; all hands, status page updated within 30 minutes. Severity 2: a major feature is unusable for many clients; fix within the working day. Severity 3: degraded or single-client impact; fix within five working days. Severity 4: cosmetic; backlog.

# Communication
Incidents are run in a dedicated chat channel with an incident commander. Client-facing updates go through the support team, never directly from engineers.

# Postmortems
Every Severity 1 and 2 incident gets a blameless postmortem within five working days, with action items tracked in Jira until closed.
"""),
    ("change-management", "Change management and deployments", ["change management", "deployment", "release", "rollback"], """
# Standard changes
Code reaches production through the continuous delivery pipeline after a reviewed pull request, green tests and a passing quality gate. Standard changes need no separate approval.

# Significant changes
Database migrations that are not backwards compatible, infrastructure changes to networking or identity, and model version releases are significant changes. They need a written change plan with a rollback step, a named approver from the owning team and a deployment window outside client peak hours.

# Freeze periods
No significant changes in the last two working days before a quarter end or during an active Severity 1 incident, unless the change is the fix.

# Rollback
Every deployment must be reversible within 30 minutes. If a rollback is not possible, the change plan must say so and name the mitigation.
"""),
    ("expenses-travel", "Expenses and travel", ["expenses", "travel", "reimbursement", "conference"], """
# What is reimbursed
Reasonable costs incurred for company business: travel, accommodation, meals while travelling, client entertainment within limits, conference tickets and professional memberships approved by the manager.

# Limits
Hotel up to 250 USD per night in most cities and 350 USD in London, New York and San Francisco. Meals up to 75 USD per day while travelling. Conference tickets up to 1,500 USD with manager approval in advance; above that, director approval. Economy class for flights under six hours.

# How to claim
Submit claims in the expense tool within 30 days of the spend with itemised receipts. Claims older than 90 days are not reimbursed. Personal credit card points are yours to keep.

# Not reimbursed
Alcohol outside client entertainment, fines, upgrades, and spending on behalf of other employees without their manager's approval.
"""),
    ("remote-work", "Remote and hybrid work", ["remote work", "hybrid", "home office", "equipment"], """
# Arrangement
Employees work from the office at least two days a week unless their role is designated remote. Remote days are agreed with the manager and recorded in the team calendar.

# Home office
The company provides a laptop, a monitor and a headset. A one-off home office allowance of 400 USD covers a desk or chair. Internet costs are not reimbursed.

# Working abroad
Working from another country for more than 10 working days in a year needs HR approval in advance because of tax and data residency rules. Client data must never be accessed from countries on the restricted list.

# Security at home
Use the VPN, keep the screen out of view of others, and never let family members use the company laptop.
"""),
    ("vendor-risk", "Vendor and third-party risk", ["vendors", "third party", "procurement", "soc2"], """
# When this applies
Any new SaaS tool, data provider, cloud service or contractor that will store or process company or client data, or that integrates with production systems.

# Assessment
Procurement collects a security questionnaire, a SOC 2 Type II report or equivalent, the data processing agreement and the sub-processor list. Security rates the vendor low, medium or high risk. High-risk vendors need a named executive sponsor and an annual reassessment.

# Approved tools
Only tools on the approved list may receive Confidential data. Engineers may trial a tool with synthetic data for 30 days without approval.

# Exit
Contracts must allow data export and deletion within 30 days of termination.
"""),
    ("secure-development", "Secure development standard", ["secure development", "code review", "dependencies", "secrets"], """
# Code review
Every change to a production repository is reviewed by someone other than the author. Reviewers check for input validation, authorisation, error handling and logging of sensitive data.

# Dependencies
Dependabot alerts are triaged weekly. Critical alerts are fixed within 7 days, high within 30 days. Pinned versions and a lock file are mandatory.

# Secrets
Secrets live in the secrets manager, never in code, configuration files or chat. A secret that is committed by mistake is rotated the same day even if the commit is removed.

# Testing and quality gates
Unit tests run on every pull request. Services keep coverage at or above 80 percent as reported by SonarCloud, and the quality gate must pass before merge.
"""),
    ("retention-backups", "Data retention and backups", ["retention", "backups", "restore", "deletion"], """
# Retention periods
Client portfolios and analysis results are kept for the life of the contract plus 12 months, then deleted. Application logs are kept for 13 months. Financial records are kept for 7 years. Recruitment data for unsuccessful candidates is deleted after 6 months.

# Backups
Production databases are backed up daily with point-in-time recovery for 35 days. Backups are encrypted and stored in a second region. A restore test is run monthly and the result is recorded.

# Deletion requests
Client deletion requests are completed within 30 days and confirmed in writing. Deletion covers primary storage, backups beyond the retention window and analytics copies.
"""),
    ("ai-tools", "Use of AI tools and assistants", ["ai", "llm", "copilot", "chatgpt", "claude"], """
# Approved tools
AI assistants on the approved list may be used for writing, coding and analysis. Enterprise accounts with data-retention disabled are mandatory; personal consumer accounts may not receive company data.

# What may not be shared
Client exposure data, personal data, credentials, unreleased financial results and security findings must not be entered into any AI tool, approved or not, unless the tool runs inside our own environment.

# Code and content
AI-generated code is reviewed like any other code and must not introduce dependencies with unknown licences. AI-written client communications are reviewed by a human before sending.

# Accountability
The person who uses the output is responsible for it. Cite the tool in the pull request description when it wrote a substantial part of a change.
"""),
]

FAQS: list[tuple[str, str, list[str], str]] = [
    ("run-probabilistic-analysis", "How do I run a probabilistic analysis in Portfolio Manager?", ["pm", "analysis"], "Open the portfolio, choose Run Analysis, pick Probabilistic, select or create analysis settings (frequency and severity distributions, number of simulation years, conservative/default/aggressive rates) and press Run. The analysis appears in the analyses list; large portfolios can take over an hour."),
    ("download-loss-metrics", "How do I download a loss metrics report?", ["reports", "loss metrics"], "Open the completed analysis, go to Reports, choose Loss Metrics and press Download. The CSV contains Gross, Net and Ceded metrics including AAL, SD-AL, CV and the AEP, OEP and TCE curves."),
    ("by-company-reports-missing", "Why are the By Company reports empty or missing?", ["reports", "by company", "account level"], "By Company reports require the Calculate Account Level Metrics option to be enabled when the analysis is run. Re-run the analysis with that option on; it increases run time."),
    ("company-ylt-size", "How big is the full company YLT export and how do I get it?", ["api", "ylt", "export"], "The full company year loss table is API only: set fullCompanyYlt to true in the analysis settings before running. The export is a zip with one CSV; for a 100,000-policy portfolio expect roughly 0.5 GB and about 5 million rows."),
    ("simulation-years", "How many simulation years should I use?", ["analysis", "settings"], "The UI offers 10,000 or 50,000 simulation years. Use 50,000 for tail metrics such as the 1-in-1,000 OEP; 10,000 is fine for quick comparisons of portfolio changes."),
    ("api-ids-guid", "My API calls fail with invalid portfolio id after moving to v6", ["api", "migration"], "PM v6 identifiers are GUIDs; v5.5 used integers. Re-read the portfolio and analysis IDs from the v3 endpoints on api.pm.cybcube.com and do not reuse v2 integer IDs."),
    ("api-key-rotation", "How do I rotate my API key?", ["api", "keys", "account"], "An account administrator opens Settings, API Keys, creates a new key, updates the integration, then revokes the old key. Keys cannot be viewed again after creation, so store the new key in your secrets manager immediately."),
    ("sso-login", "Can we log in with single sign-on?", ["account", "sso", "login"], "Yes. SAML single sign-on is available on enterprise plans. Your IT administrator sends the identity provider metadata to support, and support enables SSO for the tenant. Password login stays available for break-glass administrators."),
    ("add-users", "How do I add a user to our tenant?", ["account", "users"], "Tenant administrators add users under Settings, Users, Invite. Choose a role: Viewer, Analyst or Administrator. The invitation link expires after 7 days."),
    ("reset-password", "How do I reset my password?", ["account", "password"], "Use Forgot password on the login page. The reset email is valid for 30 minutes. If your organisation uses SSO, reset the password with your identity provider instead."),
    ("import-portfolio-format", "What file format does the portfolio import accept?", ["import", "portfolio"], "CSV or XLSX using the import template. Required columns include company name, website or domain, country, industry, revenue, contract type, limit, deductible and the v6 fields Patch Management, Network Segmentation and Data Backup Frequency. Rows failing validation are listed in the import report."),
    ("losses-differ-between-runs", "Why do losses differ slightly between two runs with the same settings?", ["analysis", "random", "seed"], "The simulation uses random draws for frequency, footprint, impact and severity. Two runs with the same settings converge at the portfolio level but individual occurrences differ. For exact reproducibility export the YLT of one run rather than re-running."),
    ("treaty-tag", "How do I assign a reinsurance treaty to policies?", ["reinsurance", "treaty"], "Fill the Treaty Tag column in the portfolio with the treaty name; separate several treaties with semicolons. Define the treaties (Quota Share or Risk Excess of Loss) in the analysis settings under Reinsurance. Loss Metrics then report Gross, Net and Ceded."),
    ("waiting-period-hours", "How is the business interruption waiting period expressed?", ["bi", "waiting period", "deductible"], "Business interruption deductibles can be set in hours as a waiting period, as well as in currency or as a percentage. The waiting period is applied at the coverage level before the policy attachment and limits."),
    ("non-affirmative", "What does non-affirmative cover mean in the results?", ["contract type", "non-affirmative"], "Contract types other than Standalone and Other are treated as non-affirmative cyber cover. Their losses are modelled as a probabilistic payout, so the expected loss is lower than for an equivalent affirmative policy."),
    ("spof-intelligence", "What is SPoF Intelligence and how is it different from Portfolio Manager?", ["spof", "products"], "SPoF Intelligence shows which single points of failure, such as cloud providers, software and service providers, your insureds depend on and how concentrated that dependency is. Portfolio Manager turns those dependencies into simulated losses through the catastrophe model."),
    ("non-modeled-spof", "A SPoF I care about is not in the modeled list. What happens to it?", ["spof", "non-modeled"], "Each scenario models the SPoFs that together cover more than 90 percent of the relevant market. A SPoF outside the list is a Non-Modeled SPoF: it is not selected as an event target, although companies that depend on it can still be affected through the aggregate footprint of modeled SPoFs."),
    ("regional-cloud", "Does the model distinguish regional and global cloud outages?", ["cloud", "regional", "3ci"], "Yes, since v6. For the regional cloud service provider scenarios 36 to 40 the model simulates single-region, multi-region and global outages, and multi-region outages share one Event Occurrence ID so the OEP treats them as one occurrence."),
    ("security-score-effect", "How do security scores change my modelled losses?", ["security score", "severity", "impact"], "Security scores feed the impact module, which decides whether an exposed company suffers a loss, and the severity module's Security modifier, which scales the loss between 0.5 and 2.0 relative to peers. Companies with missing scores get a modifier of 1.0."),
    ("supported-browsers", "Which browsers are supported?", ["account", "browsers"], "The current and previous major versions of Chrome, Edge, Firefox and Safari. Internet Explorer is not supported. Large report downloads work best in Chrome."),
    ("data-retention-client", "How long do you keep our portfolio data?", ["data", "retention"], "Portfolios and analysis results are kept for the life of the contract plus 12 months, after which they are deleted. You can request earlier deletion through support; deletion is confirmed in writing within 30 days."),
    ("support-ticket", "How do I raise a support ticket and what are the response times?", ["support", "sla"], "Email support or use the Help button in the application. Severity 1 issues (platform unavailable) are acknowledged within 1 hour on business days; other issues within 1 business day. Include the tenant name, portfolio ID and analysis ID."),
    ("analysis-stuck", "My analysis has been running for hours. Is it stuck?", ["analysis", "performance"], "Portfolios above 100,000 policies at 50,000 simulation years can take several hours, longer with Calculate Account Level Metrics enabled. If the status has not changed for more than 6 hours, raise a support ticket with the analysis ID."),
    ("export-security-scores", "Can I export the security scores for my portfolio?", ["api", "security scores", "export"], "Yes. In the application use Export, Security Scores on the portfolio page, or call the API endpoint /odap/portfolios/export/v3/security-scores/ followed by the portfolio ID. The export lists the six control category scores per matched company."),
    ("unmatched-companies", "How do I see which companies in my portfolio were not matched?", ["import", "matching", "api"], "Use the company information download, available in PM v6.30 and later: Export, Company Information in the application, or the API endpoint /odap/portfolios/export/v1/company-information/unmatched/ followed by the portfolio ID. Improve matching by supplying the company website or domain."),
]


def _front(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def write_corpus(out: Path) -> dict[str, int]:
    counts = {}
    pd = out / "product-docs"; pd.mkdir(parents=True, exist_ok=True)
    for slug, title, url, tags, body in PRODUCT_DOCS:
        (pd / f"{slug}.md").write_text(_front({"id": f"doc-{slug}", "title": title, "collection": "product-docs", "url": url, "tags": tags, "fictional": False})
                                       + body.strip() + "\n")
    counts["product-docs"] = len(PRODUCT_DOCS)
    po = out / "policies"; po.mkdir(parents=True, exist_ok=True)
    for slug, title, tags, body in POLICIES:
        (po / f"{slug}.md").write_text(_front({"id": f"pol-{slug}", "title": title, "collection": "policies", "url": f"internal://policies/{slug}", "tags": tags, "fictional": True})
                                       + body.strip() + "\n")
    counts["policies"] = len(POLICIES)
    fq = out / "faqs"; fq.mkdir(parents=True, exist_ok=True)
    for slug, question, tags, answer in FAQS:
        (fq / f"{slug}.md").write_text(_front({"id": f"faq-{slug}", "title": question, "collection": "faqs", "url": f"internal://faqs/{slug}", "tags": tags, "fictional": True})
                                       + f"# {question}\n{answer}\n")
    counts["faqs"] = len(FAQS)
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    a = ap.parse_args()
    print(write_corpus(Path(a.out)))
