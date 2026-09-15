# Merchant Master Pipeline

Source script: [mercent.py](mercent.py)

## Purpose

This pipeline turns `track1_merchants_master.csv` into a merchant dimension for transaction aggregation, category performance, onboarding controls, settlement-account review, and chargeback risk analysis.

## Processing steps

1. Profiles merchant category, business type, merchant status, and city distributions.
2. Normalizes `merchant_id` by uppercasing, removing non-alphanumeric characters, and adding `MCH` to numeric IDs.
3. Cleans merchant names by standardizing connectors, punctuation, whitespace, and title case.
4. Standardizes business types into categories such as Private Limited, Public Limited, Proprietorship, Partnership / LLP, and Individual.
5. Groups category variants using keyword rules and fuzzy matching into analytical categories including Food & Beverage, Retail & Groceries, Medical & Health, Electronics & Tech, Travel & Transport, and Education.
6. Canonicalizes city names with acronym and fuzzy matching rules and formats state names.
7. Maps merchant status to `ACTIVE`, `INACTIVE`, `SUSPENDED`, or `UNKNOWN`.
8. Cleans MCC values to digits and pads three-digit codes. When MCC is missing, it makes limited category-based inferences for high-confidence categories; otherwise it preserves missingness.
9. Parses average ticket size from currency text, converts negative magnitudes to positive values, and imputes missing values first by category median and then by global median.
10. Parses onboarding dates, including Unix epochs, and exposes `has_onboarding_date`.
11. Preserves and sanitizes settlement account or IBAN-like values, flags masked accounts through `is_masked_account`, and uses `UNKNOWN_ACCOUNT` for missing accounts.
12. Deduplicates normalized merchant IDs by retaining the richest row and then the newest onboarding date.

## Output schema

The current script writes `updated.csv`. The workspace also contains `cleaned_merchants.csv` with 4,343 rows from an existing cleaning run. The analytical merchant fields include `merchant_id`, `merchant_name`, `merchant_category`, `mcc`, `business_type`, `city`, `state`, `has_onboarding_date`, `onboarding_date`, `is_masked_account`, `settlement_account`, `merchant_status`, and `declared_avg_ticket_size`.

## Measured outcome

The raw source has 6,211 records, including a header-like first data record in the current file. The existing cleaned merchant artifact has 4,343 rows. Because this artifact predates or differs from the current script output naming and execution, rerun `python mercent.py` to produce a fresh `updated.csv` and use that run's printed counts as the authoritative result.

## Finance and risk calculations enabled

Join `merchant_id` to transactions and chargebacks to calculate transaction value, average ticket size, failed rate, dispute count, disputed amount, and chargeback-to-transaction ratio by merchant and category. Flag merchants with repeated disputes, sudden transaction spikes, high disputed value, suspended status, missing onboarding dates, masked settlement accounts, or unusually high category-adjusted ticket sizes.

## Important interpretation rules

Inferred MCCs and category-median ticket sizes are engineered values, not verified merchant declarations. Fuzzy category and city matching improves joinability but should be reviewed when a high-impact risk decision depends on it. Settlement-account masking is a privacy and data-quality signal, not proof of fraud.