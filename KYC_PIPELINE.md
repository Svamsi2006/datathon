# KYC Customer Pipeline

Source script: [kyc.py](kyc.py)

## Purpose

This pipeline builds a gold customer KYC master from `track1_kyc_records.csv`. The result supports customer identity joins, KYC completion analysis, income segmentation, risk-segment analysis, and investigation of users connected to disputed or suspicious transactions.

## Processing steps

1. Normalizes user identifiers by extracting digits and rebuilding them as `USR<digits>`.
2. Formats names in title case and trims surrounding whitespace.
3. Uppercases and removes non-alphanumeric characters from PAN values. Empty or null PAN values become `MISSING_PAN`.
4. Cleans Aadhaar values by extracting digits while preserving leading zeroes from string input. Missing values become `MISSING_AADHAAR`.
5. Classifies Aadhaar values as `VALID_12_DIGIT`, `PARTIAL_4_DIGIT`, `INVALID_LENGTH`, or `MISSING`.
6. Standardizes state, occupation, and risk segment text. Common city aliases such as Bombay, Dilli, Hyd, BLR, LKO, and JPR are mapped to canonical city names.
7. Parses monthly income strings containing `Rs`, `INR`, currency symbols, commas, `k`, or lakh notation. Invalid or missing amounts are filled with the overall median income. Negative input is converted to a positive magnitude.
8. Maps KYC status variants to `VERIFIED`, `PENDING`, `REJECTED`, or `UNKNOWN`.
9. Parses date of birth and signup timestamps, including ten-digit Unix epochs. Missing dates are exposed through `is_dob_missing` and `is_signup_time_missing`.
10. Sorts by normalized user and signup time, then keeps the latest record for each user.

## Output schema

The script writes `cleaned_kyc_data.csv` with identity, demographic, income, KYC status, risk, date, and data-quality fields. Its final fields include `id_validation_status`, `is_dob_missing`, and `is_signup_time_missing`.

## Measured outcome

The script run processed 36,400 raw records and produced 28,920 unique master users. The reduction is caused by one-record-per-user survivorship, not by dropping rows simply because a field was missing. The Aadhaar null-handling fix ensures missing numeric values are classified safely instead of crashing the pipeline.

## Finance and risk calculations enabled

Calculate KYC completion as verified users divided by unique users, with separate pending, rejected, and unknown populations. Join `user_id` to transactions to compare transaction count, transaction value, failure rate, and dispute amount across KYC statuses and risk segments. A rejected or unverified customer with repeated high-value disputes should be investigated as a risk signal, not automatically labeled as fraud.

## Important interpretation rules

Income median fill is an analytical estimate and must not be presented as a reported customer income. Aadhaar length validates structure only; it does not prove document authenticity. The synthetic data must not be used for real onboarding, credit, or fraud decisions.