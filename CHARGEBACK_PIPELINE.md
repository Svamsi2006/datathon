# Chargeback and Dispute Pipeline

Source script: [track.py](track.py)

## Purpose

This pipeline converts `track1_chargebacks.json` into a relational dispute ledger. It standardizes complaint, transaction, customer, and merchant keys so chargebacks can be joined to payment, KYC, and merchant data without losing records to formatting differences.

## Processing steps

1. Loads the JSON array as a tabular record set and profiles reason codes, resolution statuses, severity, and intake channels.
2. Normalizes complaint, transaction, user, and merchant identifiers into `CBK`, `TXN`, `USR`, and `MCH` formats. Numeric-only IDs receive the relevant prefix; missing keys become `UNKNOWN_*`.
3. Extracts disputed amounts from currency text, converts negative magnitudes to positive values, fills missing amounts with the dispute-pool median, and rounds to two decimals.
4. Maps severity to `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `UNKNOWN`.
5. Maps resolution status to `OPEN`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`, `CLOSED`, or `UNKNOWN`.
6. Uppercases and trims dispute channels.
7. Maps free-text reason codes into `FRAUD_OR_ATO`, `DUPLICATE_PROCESSING`, `MERCHANT_OR_DELIVERY_ISSUE`, `AMOUNT_MISMATCH`, `GENERAL_DISPUTE`, or `UNCATEGORIZED`.
8. Parses transaction, reported, and bank-response timestamps, including numeric epochs.
9. Calculates `resolution_sla_days` as bank response minus reported date. It flags `is_sla_violation` when the response exceeds 14 days and `has_temporal_anomaly` when the response appears before the report.
10. Deduplicates complaint IDs by retaining the row with the highest non-null field count.

## Output schema

The script writes `cleaned_chargebacks.csv` with complaint, transaction, customer, merchant, timestamp, amount, semantic reason, resolution, SLA, severity, and channel fields. It retains the standardized keys needed for relational joins.

## Measured outcome

The raw JSON contains 2,884 dispute records. The existing cleaned output contains 2,800 rows after complaint-level survivorship deduplication. The reduction prevents duplicate complaints from inflating dispute counts and disputed amounts.

## Finance and risk calculations enabled

Join `txn_id` to the UPI ledger to calculate chargeback count, disputed amount, and chargeback-to-transaction ratio. Group by `merchant_id`, `user_id`, merchant category, reason category, severity, channel, or resolution status. Use `resolution_sla_days` to report average response time and late-resolution rates. Use `FRAUD_OR_ATO` and repeated user or merchant keys as investigation queues, not automatic conclusions.

## Important interpretation rules

Median-filled disputed amounts are estimates and must be labeled in downstream reporting. A temporal anomaly means the source timestamps are inconsistent; it does not establish when the real-world event occurred. Join coverage must be measured explicitly because normalized keys can still refer to entities absent from the other source tables.