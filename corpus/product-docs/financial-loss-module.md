---
id: doc-financial-loss-module
title: Financial loss module and reinsurance
collection: product-docs
url: https://docs.cybcube.com/event-modeling-v6/financial-loss-module?root=599
tags: [financial loss, deductible, limit, reinsurance, quota share, xol]
fictional: false
---
# Applying policy terms
Ground-up loss becomes insured loss in a fixed order: coverage-level deductibles and sublimits first (expressed in currency, as a percentage, or as hours for the business-interruption waiting period), then the policy attachment, then the occurrence deductible and limit, then the annual aggregate limit when the same company is hit more than once in a simulation year, and finally the participation percentage.

# Non-affirmative cover
Contract types other than Standalone and Other are treated as non-affirmative, and their losses are a probabilistic payout rather than a certain one.

# Reinsurance treaties
Two treaty types are supported. Quota Share takes a ceded percentage with an optional annual treaty limit. Risk Excess of Loss takes an attachment, a limit, a layer ceded percentage and an optional annual treaty limit; in years where the treaty limit is exceeded, all companies are scaled down equally. Treaties are assigned to policies through the Treaty Tag column, which accepts several tags separated by semicolons. Treaty stacking lets a quota share sit on top of an excess-of-loss layer.
