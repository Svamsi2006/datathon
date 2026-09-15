# Sentinel Risk Engine

**TransOrg AgentIQ Datathon, Track 1: FinTech and BFSI**

Sentinel Risk Engine is a data preparation and analytics foundation for UPI fraud, customer KYC, merchant risk, and chargeback analysis. The workspace contains four Python pipelines that convert intentionally messy synthetic financial records into normalized, joinable tables.

The cleaning rules are based on [track1_dataset_notes.txt](track1_dataset_notes.txt). The source data is synthetic and intended for educational and datathon use, not for production financial decisions.

## Live Application

- Dashboard: [Fraud and Risk Analytics Dashboard](https://dataton.ai.studio/)
- Data source: [Google Sheets](https://docs.google.com/spreadsheets/d/1PuOO9_75OPhBdJWXBBcy-hPkVHHG7Er_XjRB-89DSI/edit?usp=sharing)

The dashboard and chat analyst can consume the cleaned tables described below. The Python files in this folder perform data engineering; they do not implement the web UI or Gemini integration.

## Documentation

- [UPI transaction pipeline](UPI_PIPELINE.md)
- [KYC customer pipeline](KYC_PIPELINE.md)
- [Merchant master pipeline](MERCHANT_PIPELINE.md)
- [Chargeback pipeline](CHARGEBACK_PIPELINE.md)

## Architecture

```text
Raw CSV/JSON files
        |
        v
Profiling -> key normalization -> financial/date parsing
        |                  |                  |
        v                  v                  v
Categorical mapping   missing-value flags   survivorship deduplication
        \                  |                  /
         v                v                 v
Analytics-ready UPI, KYC, merchant, and chargeback tables
                         |
                         v
Relational joins and risk metrics
                         |
                         v
Dashboard and conversational analytics layer
```

Expected joins from the dataset specification:

| Relationship | Join key |
| --- | --- |
| UPI to KYC | `user_id` |
| UPI to merchants | `merchant_id` |
| Chargebacks to UPI | `txn_id` |
| Chargebacks to KYC | `user_id` |
| Chargebacks to merchants | `merchant_id` |

## Financial and risk outcomes

The normalized tables support these calculations:

- Total transaction count and transaction amount
- Average transaction value
- Successful, failed, pending, and unknown transaction rates
- Missing-UTR transaction count and rate
- Chargeback count, disputed amount, and chargeback-to-transaction ratio
- Dispute rate and disputed amount by merchant or category
- KYC verification, pending, and rejection rates
- High-risk users and merchants with repeated disputes
- Average dispute response time and disputes exceeding the 14-day SLA flag
- Transactions before customer signup or merchant onboarding, when the tables are joined
- Duplicate transaction and duplicate complaint detection before aggregation

Amounts are cleaned for analysis, but the original raw files remain available for audit. Negative monetary values are converted to absolute values because these fields represent transaction or dispute magnitude; debit/credit direction is not modeled by these scripts.

## Current generated results

The current folder contains these measured source and output sizes:

| Pipeline | Raw records | Existing cleaned records | Main result |
| --- | ---: | ---: | --- |
| UPI | 20,400 | 20,000 | One surviving row per normalized transaction ID |
| KYC | 36,400 | 28,920 | One surviving row per normalized user ID |
| Merchants | 6,211 | 4,343 | One surviving row per normalized merchant ID |
| Chargebacks | 2,884 | 2,800 | One surviving row per normalized complaint ID |

Rows are reduced only through entity survivorship deduplication in the scripts or through the existing generated artifacts. Missing values are generally imputed or flagged rather than discarded. Always rerun the relevant script when producing a fresh artifact.

## Running the pipelines

Run from this folder:

```powershell
python upi.py
python kyc.py
python mercent.py
python track.py
```

The current script entry points write `updated_upi.csv`, `cleaned_kyc_data.csv`, `updated.csv`, and `cleaned_chargebacks.csv`, respectively. The folder also contains `cleaned_upi.csv` and `cleaned_merchants.csv`, which are existing cleaned artifacts with compatible analytical schemas but are not the output filenames used by the current UPI and merchant scripts.

## Agent and dashboard contract

The UI or chat analyst should answer questions from normalized columns and computed aggregates, not from raw text. Example questions include:

- Which merchant has the highest chargeback count or disputed amount?
- Which category has the highest chargeback-to-transaction ratio?
- Show daily transaction value and failed transaction trends.
- Which users have repeated disputes and rejected KYC?
- Show disputes reported after seven days or resolved beyond the 14-day SLA threshold.
- Which transactions are missing UTRs or have invalid timestamps?

Any live Gemini, OpenRouter, Groq, or other model routing configuration belongs to the application layer and is not present in these local Python scripts. The analyst should cite the cleaned data and metric definitions when responding.

## Data governance notes

- Preserve raw files for traceability.
- Treat imputed amounts and inferred MCC values as engineered estimates.
- Keep `UNKNOWN`, missing, and invalid flags visible in analysis.
- Validate foreign-key coverage after joining the four cleaned tables.
- Do not interpret synthetic findings as real customer, merchant, or fraud decisions.