# UPI Transaction Pipeline

Source script: [upi.py](upi.py)

## Purpose

This pipeline converts `track1_upi_transactions.csv` into a transaction ledger suitable for payment-volume, failure, missing-UTR, and fraud-ring analysis. It keeps the raw data available and creates normalized analytical columns.

## Processing steps

1. Loads the CSV and lowercases and trims column names.
2. Profiles common status, UTR, and amount values before transformation.
3. Normalizes `txn_id`, `user_id`, and `merchant_id` by uppercasing, removing punctuation, and adding `TXN`, `USR`, or `MCH` prefixes to numeric identifiers. Missing identifiers become `UNKNOWN_*` values.
4. Maps status variants such as `SUCCESS`, `TXN_SUCCESS`, `COMPLETED`, `FAIL`, `DECLINED`, `PENDING`, and `PROCESSING` to `SUCCESS`, `FAILED`, or `PENDING`. Unrecognized values become `UNKNOWN`.
5. Removes spaces, hyphens, and symbols from UTRs. Missing UTRs are flagged in `is_missing_utr` and represented as `UNAVAILABLE` in the cleaned output.
6. Extracts numeric amounts from currency strings such as `Rs. 1,500.50` or `₹-400`. Invalid values become missing, then are filled first with the normalized user's median amount and finally with the global median. Amounts are rounded to two decimals and made positive.
7. Parses mixed timestamps and ten-digit Unix epochs into a standard timestamp string. `has_valid_timestamp` records whether parsing succeeded.
8. Deduplicates normalized transaction IDs using survivorship: the row with the most non-null fields wins, followed by the newest cleaned timestamp.

## Output schema

The script maps the result to `txn_id`, `user_id`, `merchant_id`, `transaction_amount`, `transaction_status`, `utr_number`, `is_missing_utr`, `timestamp`, and `has_valid_timestamp`.

The current entry point writes `updated_upi.csv`. The workspace also contains `cleaned_upi.csv` with 20,000 rows; it is an existing cleaned artifact and not the filename currently written by `upi.py`.

## Measured outcome

The raw file contains 20,400 transaction records. The existing cleaned output contains 20,000 rows, indicating 400 rows were removed by normalized transaction-key survivorship. This protects transaction totals and dispute ratios from duplicate inflation while retaining the richest version of each transaction.

## Finance and risk calculations enabled

Use `transaction_amount` for total value, average ticket value, value by day, merchant, category, or KYC status, and successful-versus-failed comparisons. Use `transaction_status` for failure and pending rates. Use `is_missing_utr` to identify transactions that need traceability review, especially successful transactions without a reference number. Join `user_id`, `merchant_id`, and `txn_id` to the other pipelines before calculating fraud or chargeback metrics.

## Important interpretation rules

Absolute-value correction fixes malformed magnitude values; it does not recover payment direction. Median imputation creates an estimate and should be identified as such in a dashboard. `UNKNOWN` keys and statuses should remain visible as data-quality populations rather than being silently removed.