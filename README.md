# 🛡️ Sentinel Risk Engine

### Advanced UPI Fraud Ring Detection, Merchant Risk Analytics & FastMCP AI Agent

**TransOrg AgentIQ Datathon — Track 1: FinTech & BFSI**

---

## 📌 Executive Summary

**Sentinel Risk Engine** is an end-to-end data engineering and real-time risk intelligence platform engineered for UPI payment networks. Designed to resolve high-noise, distributed transaction anomalies, Sentinel bridges high-throughput Python data cleaning pipelines with a modern Next.js/React risk monitoring dashboard and an in-memory **FastMCP Natural Language Query (NLQ) AI Analyst**.

The system automates the ingestion, normalization, entity resolution, and relational linking of over **65,000+ raw records** across four core payment domains—without discarding messy rows arbitrarily or relying on black-box heuristics.

---

## 🏗️ End-to-End Architecture

```text
  [ Raw CSV / JSON Artifacts ]
  ├── track1_upi_transactions.csv (20,400)
  ├── track1_kyc_records.csv       (36,400)
  ├── track1_merchants_master.csv  (6,211)
  └── track1_chargebacks.json      (2,884)
                   │
                   ▼
  [ Vectorized ETL & Entity Resolution Engine ]
  ├── upi.py     ──► Regex sanitization, status canonicalization, Unix date parsing
  ├── kyc.py     ──► Multi-format PAN/Aadhaar validation, income normalization
  ├── mercent.py ──► Fuzzy city mapping, MCC extraction, business type standardization
  └── track.py   ──► JSON flatten, complaint severity mapping, 14-day SLA tagging
                   │
                   ▼
  [ Production-Ready Normalized Store ]
  ├── updated_upi.csv        (20,000 surviving entities)
  ├── cleaned_kyc_data.csv   (28,920 surviving entities)
  ├── updated.csv            (4,343 surviving entities)
  └── cleaned_chargebacks.csv(2,800 surviving entities)
                   │
                   ▼
  [ Application & Visualization Tier ]
  ┌─────────────────────────────────────────────────────────────┐
  │                 SENTINEL WEB DASHBOARD                      │
  │  ├── Real-time Dynamic In-Memory Store                      │
  │  ├── Portfolio Metric Cards & Excessive Dispute Monitor     │
  │  ├── Velocity, Hourly Peak & ATO Spike Visualizers          │
  │  └── FastMCP AI Analyst Engine (Zero-Latency NLQ Core)      │
  └─────────────────────────────────────────────────────────────┘

```

---

## 🔗 Relational Data Model & Join Schema

The four pipelines standardize disparate identifier patterns (`USR-12345`, `usr 12345`, `MCH_1234`, etc.) into strictly typed primary and foreign keys:

| Primary Entity | Relational Key | Joined Entity | Foreign Key | Target Analysis |
| --- | --- | --- | --- | --- |
| **`pay`** (UPI Transactions) | `user_id` | **`people`** (KYC Master) | `user_id` | Customer risk tiers, KYC completion vs. fraud velocity |
| **`pay`** (UPI Transactions) | `merchant_id` | **`shops`** (Merchant Master) | `merchant_id` | Category-level risk, MCC verification, settlement leakage |
| **`snags`** (Chargebacks) | `txn_id` | **`pay`** (UPI Transactions) | `txn_id` | Dispute latency, UTR mismatch correlation, amount variance |
| **`snags`** (Chargebacks) | `user_id` | **`people`** (KYC Master) | `user_id` | Serial dispute filers, collusion clusters, rejected KYC risk |
| **`snags`** (Chargebacks) | `merchant_id` | **`shops`** (Merchant Master) | `merchant_id` | Excessive Dispute Program (Visa/Mastercard 1% threshold) |

---

## ⚙️ Data Engineering & Pipeline Specs

### Pipeline Execution Summary

```bash
# Execute the entire cleaning suite:
python upi.py      # Outputs: updated_upi.csv
python kyc.py      # Outputs: cleaned_kyc_data.csv
python mercent.py  # Outputs: updated.csv
python track.py    # Outputs: cleaned_chargebacks.csv

```

### Ingestion & Cleaning Metrics

| Pipeline | Source File | Raw Count | Cleaned Count | Core Engineering Highlights |
| --- | --- | --- | --- | --- |
| **`upi.py`** | `track1_upi_transactions.csv` | 20,400 | **20,000** | Strict regex extraction for `TXNxxxxx`, status canonicalization (`SUCCESS`, `FAILED`, `PENDING`), timestamp harmonization (handling Epoch floats), missing-UTR isolation. |
| **`kyc.py`** | `track1_kyc_records.csv` | 36,400 | **28,920** | Entity survivorship deduplication on `user_id`, income vector normalization, PAN/Aadhaar format verification, geographic normalization. |
| **`mercent.py`** | `track1_merchants_master.csv` | 6,211 | **4,343** | City mapping (`Jalandar` ➔ `Jalandhar`, `Mumbay` ➔ `Mumbai`, `Poona` ➔ `Pune`, `JPR` ➔ `Jaipur`), business type standardization (`private_limited` ➔ `Private Limited`), non-destructive IBAN sanitization, raw MCC digit isolation. |
| **`track.py`** | `track1_chargebacks.json` | 2,884 | **2,800** | JSON parsing, absolute dispute amount extraction, reason code grouping, SLA computation (`dispute_delay_days` and `exceeds_14d_sla`). |

---

## 🖥️ Sentinel Web Dashboard Features

The web frontend is designed around a mission-critical, dark-mode cybersecurity interface providing immediate situational awareness over portfolio health.

### 1. Dynamic Data Layer

* **Dynamic Dataset Import:** Seamlessly parses tabular datasets and Google Sheets exports directly into browser memory.
* **Non-Blocking Compute:** In-memory memoization ensures instant filtering across 20,000+ transaction rows with zero UI freeze.

### 2. Executive Portfolio Telemetry (KPI Suite)

* **Gross Payment Volume (GPV):** Total transaction volume, aggregate monetary turnover, and Average Transaction Value (ATV).
* **Payment State Ratios:** Automated breakdowns of `SUCCESS`, `FAILED`, and `PENDING` payment streams.
* **Dispute & Exposure Metrics:** Aggregate dispute counts, total disputed liability, and chargeback-to-transaction ratios.
* **Missing UTR Index:** Real-time visibility into transactions missing bank reference numbers (a primary vector for synthetic fraud).

### 3. Merchant Risk & Fraud Ring Visualizers

* **Excessive Dispute Program Monitor:** Automatically flags all merchants exceeding the regulatory **1.0% dispute threshold** (e.g., detecting anomaly spikes like Babu Khatri / MCH1320).
* **Sector Risk Index:** Aggregates dispute density by business category (Apparel & Fashion, Electronics, Gaming, etc.).
* **Midnight Velocity Spike Detector:** Identifies off-hours account takeover (ATO) activity and high-frequency dispute surges.
* **KYC Status vs. Dispute Matrix:** Cross-analyzes chargeback frequency across `VERIFIED`, `PENDING`, and `REJECTED` customer profiles.

---

## 🤖 Module 5: FastMCP In-Memory AI Analyst (NLQ Core)

The **Natural Language Query Engine** allows fraud analysts, auditors, and executive teams to query live transaction arrays using plain English.

### Architecture: Zero-Hallucination In-Memory Tool Calling

Rather than feeding 20,000 raw rows to an LLM (which introduces latency, privacy risks, and mathematical hallucinations), Sentinel utilizes a **Deterministic Two-Tier Intent Architecture**:

1. **Semantic Parameter Routing:** The LLM receives only the user's prompt and acts as an intent parser, mapping questions to structured tool calls.
2. **Native Vector Execution:** The browser frontend executes the parsed intent directly against the active in-memory arrays (`pay`, `snags`, `shops`, `people`) using compiled JavaScript `filter` and `reduce` operations. Results compute in **under 10ms**.

### Conversational UI & Experience

* **Sticky Bottom Input Bar:** Stays anchored at the base of the screen with a clean prompt input and run button.
* **Horizontal Benchmark Carousel:** Instant, single-click datathon benchmark queries situated directly above the prompt bar.
* **Auto-Scrolling Viewport:** Viewport smoothly auto-scrolls (`scrollIntoView`) on every response to maintain focus.
* **Live Relational Trace:** Every analytical card displays an inspectable relational execution trail detailing the joins and aggregations performed (e.g., `READ snags ➔ JOIN shops ON merchant_id ➔ AGGREGATE ➔ LIMIT 10`).
* **Direct Data Export:** Copy results as TSV or download filtered records directly as CSV from the analyst bubble.

### Datathon-Mandated Benchmark Queries Supported

* *"Which merchant has the highest chargeback count?"*
* *"Compare successful vs failed transactions by day"*
* *"Show top 10 users by disputed amount"*
* *"Find merchants with dispute rate above 1% threshold"*
* *"What is the dispute rate of unverified users?"*
* *"What is the hourly peak for fraudulent transactions?"*
* *"Total chargeback liability breakdown by dispute reason"*
* *"Average transaction value of verified vs rejected KYC users"*

---

## 🚀 Getting Started

### Prerequisites

* **Python 3.10+** (with `pandas` and `numpy`)
* **Node.js 18+** & **npm**

### 1. Data Pipeline Setup

```bash
# Clone the repository
git clone https://github.com/your-org/sentinel-risk-engine.git
cd sentinel-risk-engine

# Install Python requirements
pip install pandas numpy

# Run the engineering scripts to generate cleaned artifacts
python upi.py
python kyc.py
python mercent.py
python track.py

```

### 2. Frontend Dashboard Setup

```bash
# Navigate to web dashboard workspace
cd web

# Install UI & Agent dependencies
npm install

# Start the local development server
npm run dev

```

Open [http://localhost:3000](http://localhost:3000) in your browser to access the dashboard.

---

## 🔒 Data Governance & Ethical Guardrails

1. **Synthetic Isolation:** All records, identifiers, PANs, and bank accounts are purely synthetic and designed specifically for the TransOrg AgentIQ Datathon.
2. **Auditability First:** Raw source files are preserved untouched; transformations use non-destructive regex and explicit survivorship flags.
3. **Engineering Transparency:** Imputed values (e.g., MCC estimations or date parsing fallbacks) are explicitly tracked with analytical flags (`is_imputed`, `has_onboarding_date`).
4. **Privacy Protection:** Personal identifiers adhere to automated redaction protocols during all AI prompt routing operations.
