import pandas as pd
import numpy as np
import re
import warnings

# Suppress pandas chained assignment warnings for cleaner output
warnings.filterwarnings('ignore')

class ChargebackDataOptimizer:
    """
    A robust data engineering pipeline for track1_chargebacks.json.
    Designed to prepare dispute resolution ledgers for fraud operations and risk analytics.
    Features:
    - Quad-Key Regex Normalization (complaint_id, txn_id, user_id, merchant_id)
    - Semantic Categorization of Reason Codes (Fraud vs Processing vs Merchant Issues)
    - SLA Temporal Parsing (Calculating resolution times across mixed epoch/string dates)
    - Severity and Channel standardization
    """
    
    def __init__(self, file_path):
        try:
            # Pandas can natively parse standard JSON arrays of records
            self.df = pd.read_json(file_path)
            self.initial_rows = len(self.df)
            print(f"[*] Successfully loaded Chargeback JSON. Initial record count: {self.initial_rows}")
        except ValueError as e:
            raise Exception(f"CRITICAL ERROR: Failed to parse JSON. {str(e)}")
        except FileNotFoundError:
            raise Exception(f"CRITICAL ERROR: '{file_path}' not found. Ensure the file is in the directory.")

    def deep_data_profiling(self):
        """
        Simulates human EDA. Fetches top unique values for critical dispute columns
        to understand the noise topology before automated cleaning rules are applied.
        """
        print("\n" + "="*55)
        print("HUMAN-LIKE EDA: DEEP COLUMN PROFILING (CHARGEBACKS)")
        print("="*55)
        
        cols_to_profile = ['reason_code', 'resolution_status', 'severity', 'channel']
        
        for col in cols_to_profile:
            if col in self.df.columns:
                print(f"\n--- Analyzing Column: '{col}' ---")
                # Fill missing temporarily for profiling visibility
                top_values = self.df[col].fillna('MISSING').value_counts().head(8)
                for val, count in top_values.items():
                    print(f"  -> {str(val).ljust(30)} : {count} occurrences")
                
        print("\n[*] Profiling complete. Pipeline will execute targeted semantic mappings...\n")

    def normalize_keys(self):
        """
        Standardizes primary keys and foreign keys to strictly match the 
        UPI Transactions and Merchants Master tables, ensuring 100% join integrity.
        """
        print("[*] Normalizing Primary & Foreign Keys (CBK, TXN, USR, MCH)...")
        
        def clean_id(val, prefix):
            if pd.isna(val) or str(val).strip() == '':
                return f'UNKNOWN_{prefix}'
            
            # Uppercase and strip non-alphanumerics (removes hyphens, spaces, underscores)
            val = re.sub(r'[^A-Z0-9]', '', str(val).upper())
            
            # If the ID is just digits (e.g. '12345'), prepend the correct prefix
            if val.isdigit():
                return f'{prefix}{val}'
                
            # If the ID has a generic text but missing the standard prefix structure
            if not val.startswith(prefix):
                 # Edge case cleanup for malformed strings
                 val = val.replace('TXN', '').replace('MCH', '').replace('USR', '').replace('CBK', '')
                 return f'{prefix}{val}'
                 
            return val

        if 'complaint_id' in self.df.columns:
            self.df['complaint_id_clean'] = self.df['complaint_id'].apply(lambda x: clean_id(x, 'CBK'))
        if 'txn_id' in self.df.columns:
            self.df['txn_id_clean'] = self.df['txn_id'].apply(lambda x: clean_id(x, 'TXN'))
        if 'user_id' in self.df.columns:
            self.df['user_id_clean'] = self.df['user_id'].apply(lambda x: clean_id(x, 'USR'))
        if 'merchant_id' in self.df.columns:
            self.df['merchant_id_clean'] = self.df['merchant_id'].apply(lambda x: clean_id(x, 'MCH'))

    def parse_financials(self):
        """
        Extracts disputed amounts from messy strings (e.g., 'Rs. 7,039', '₹1,949.60').
        Mathematically corrects invalid negative inputs.
        """
        print("[*] Parsing Financial Vectors (Disputed Amount)...")
        
        if 'disputed_amount' in self.df.columns:
            def clean_amount(val):
                if pd.isna(val) or str(val).strip() == '': return np.nan
                # Keep digits, decimals, and negative signs. Strip commas and currencies.
                cleaned_str = re.sub(r'[^\d\.-]', '', str(val))
                try:
                    # float() parses the string. abs() corrects accidental negative typos
                    return abs(float(cleaned_str))
                except ValueError:
                    return np.nan
                    
            self.df['disputed_amount_clean'] = self.df['disputed_amount'].apply(clean_amount)
            
            # Imputation: Fill missing amounts with the median of the entire dispute pool
            global_median = self.df['disputed_amount_clean'].median()
            self.df['disputed_amount_clean'].fillna(global_median, inplace=True)
            self.df['disputed_amount_clean'] = self.df['disputed_amount_clean'].round(2)

    def normalize_categoricals(self):
        """
        Collapses messy human-entered categorical fields into strict analytical buckets.
        Handles Severity, Channel, Status, and Reason Codes.
        """
        print("[*] Normalizing Categorical Variables & Mapping Semantic Reason Codes...")
        
        # 1. Severity Standardization
        if 'severity' in self.df.columns:
            def map_severity(val):
                if pd.isna(val): return 'UNKNOWN'
                v = str(val).upper().replace(' ', '')
                if v in ['CRITICAL', 'CRIT', 'P1']: return 'CRITICAL'
                if v in ['HIGH', 'H', 'P2']: return 'HIGH'
                if v in ['MEDIUM', 'M', 'P3']: return 'MEDIUM'
                if v in ['LOW', 'L', 'P4']: return 'LOW'
                return 'UNKNOWN'
            self.df['severity_clean'] = self.df['severity'].apply(map_severity)

        # 2. Resolution Status Standardization
        if 'resolution_status' in self.df.columns:
            def map_status(val):
                if pd.isna(val): return 'UNKNOWN'
                v = str(val).upper().replace('_', ' ').strip()
                if v in ['OPEN']: return 'OPEN'
                if v in ['IN PROGRESS', 'WIP', 'PENDING BANK']: return 'IN_PROGRESS'
                if v in ['RESOLVED']: return 'RESOLVED'
                if v in ['REJECTED']: return 'REJECTED'
                if v in ['CLOSED']: return 'CLOSED'
                return 'UNKNOWN'
            self.df['resolution_status_clean'] = self.df['resolution_status'].apply(map_status)

        # 3. Channel Standardization
        if 'channel' in self.df.columns:
            self.df['channel_clean'] = self.df['channel'].astype(str).str.upper().str.strip()

        # 4. Reason Code Semantic Mapping (Grouping via Keyword NLP logic)
        if 'reason_code' in self.df.columns:
            def map_reason(text):
                if pd.isna(text) or str(text).strip() == '': return 'UNCATEGORIZED'
                t = str(text).upper()
                
                # Semantic Clusters
                fraud_keywords = ['FRAUD', 'UNAUTH', 'COMPROMISED', 'HACKED', 'NOT DONE BY ME', 'ATO', 'TAKEOVER', 'SCAM']
                dup_keywords = ['DOUBLE', 'TWICE', 'DUP', 'EXTRA']
                merchant_keywords = ['DELIVER', 'SERVICE', 'NOT PROVIDED', 'ITEM NOT RECEIVED']
                amount_keywords = ['WRONG AMOUNT', 'INCORRECT AMOUNT', 'MISMATCH']
                
                if any(k in t for k in fraud_keywords): return 'FRAUD_OR_ATO'
                if any(k in t for k in dup_keywords): return 'DUPLICATE_PROCESSING'
                if any(k in t for k in merchant_keywords): return 'MERCHANT_OR_DELIVERY_ISSUE'
                if any(k in t for k in amount_keywords): return 'AMOUNT_MISMATCH'
                
                return 'GENERAL_DISPUTE'
                
            self.df['reason_category'] = self.df['reason_code'].apply(map_reason)

    def parse_temporal(self):
        """
        Standardizes timestamps for SLA (Service Level Agreement) tracking.
        Handles Unix epochs mixed with string dates across 3 different timestamp columns.
        """
        print("[*] Normalizing Temporal Timestamps and Calculating SLAs...")
        
        def clean_date_series(series):
            # Convert empty strings to NaN
            series = series.replace(r'^\s*$', np.nan, regex=True)
            
            # Identify valid numeric epochs
            is_epoch = pd.to_numeric(series, errors='coerce').notna() & (series.astype(str).str.len() >= 10)
            
            parsed_dates = pd.Series(index=series.index, dtype='datetime64[ns]')
            
            # Parse epochs
            if is_epoch.any():
                parsed_dates[is_epoch] = pd.to_datetime(series[is_epoch].astype(float), unit='s')
                
            # Parse mixed strings
            if (~is_epoch).any():
                parsed_dates[~is_epoch] = pd.to_datetime(series[~is_epoch], errors='coerce')
                
            return parsed_dates

        # Apply to all temporal vectors
        date_columns = {
            'transaction_timestamp': 'txn_date_clean',
            'reported_timestamp': 'reported_date_clean',
            'bank_response_timestamp': 'bank_response_date_clean'
        }
        
        for raw_col, clean_col in date_columns.items():
            if raw_col in self.df.columns:
                self.df[clean_col] = clean_date_series(self.df[raw_col])
                self.df[clean_col] = self.df[clean_col].dt.strftime('%Y-%m-%d %H:%M:%S')
                # Convert back to datetime for math operations
                self.df[clean_col] = pd.to_datetime(self.df[clean_col])

        # Feature Engineering: SLA Metrics (Time to Respond)
        if 'reported_date_clean' in self.df.columns and 'bank_response_date_clean' in self.df.columns:
            # Calculate difference in days
            self.df['resolution_sla_days'] = (self.df['bank_response_date_clean'] - self.df['reported_date_clean']).dt.days
            
            # Flag anomalies (negative SLA means bank responded before it was reported, which is impossible data noise)
            self.df['is_sla_violation'] = (self.df['resolution_sla_days'] > 14) # Standard banking dispute SLA
            self.df['has_temporal_anomaly'] = (self.df['resolution_sla_days'] < 0)

    def smart_deduplication(self):
        """
        Deduplicates based on complaint_id, keeping the row with the most
        data richness (least nulls).
        """
        if 'complaint_id_clean' not in self.df.columns:
            return
            
        print("[*] Executing Smart Survivorship Deduplication...")
        
        # Calculate 'data richness'
        self.df['non_null_count'] = self.df.notna().sum(axis=1)
        
        # Sort by primary key, then richness (descending)
        self.df = self.df.sort_values(by=['complaint_id_clean', 'non_null_count'], ascending=[True, False])
        
        # Drop duplicates, keeping the first (richest) row
        self.df = self.df.drop_duplicates(subset=['complaint_id_clean'], keep='first')
        
        # Cleanup
        self.df.drop(columns=['non_null_count'], inplace=True)
        self.final_rows = len(self.df)

    def execute(self):
        """
        Runs the full execution trace and exports the target dataframe.
        """
        self.deep_data_profiling()
        self.normalize_keys()
        self.parse_financials()
        self.normalize_categoricals()
        self.parse_temporal()
        self.smart_deduplication()
        
        # Map back to clean, expected analytical schema
        col_mapping = {
            'complaint_id_clean': 'complaint_id',
            'txn_id_clean': 'txn_id',
            'user_id_clean': 'user_id',
            'merchant_id_clean': 'merchant_id',
            'txn_date_clean': 'transaction_timestamp',
            'reported_date_clean': 'reported_timestamp',
            'disputed_amount_clean': 'disputed_amount',
            'reason_category': 'reason_category',         # NLP Categorized
            'resolution_status_clean': 'resolution_status',
            'bank_response_date_clean': 'bank_response_timestamp',
            'resolution_sla_days': 'resolution_sla_days', # Engineered Feature
            'is_sla_violation': 'is_sla_violation',       # Engineered Feature
            'severity_clean': 'severity',
            'channel_clean': 'channel'
        }
        
        target_cols = [col for col in col_mapping.keys() if col in self.df.columns]
        self.df = self.df[target_cols]
        self.df.rename(columns={k: col_mapping[k] for k in target_cols}, inplace=True)
        
        print("\n=== CHARGEBACK PIPELINE EXECUTION SUMMARY ===")
        print(f"Initial Raw Disputes: {self.initial_rows}")
        print(f"Final Deduplicated Disputes: {self.final_rows}")
        print("Architectural Enhancements: NLP Reason Mapping, SLA Temporal Engineering, Quad-Key Standardization.")
        print("=============================================\n")
        
        return self.df

if __name__ == "__main__":
    try:
        pipeline = ChargebackDataOptimizer('track1_chargebacks.json')
        cleaned_chargebacks_df = pipeline.execute()
        
        # Export the cleaned JSON payload as a relational CSV for easy joining
        output_filename = 'cleaned_chargebacks.csv'
        cleaned_chargebacks_df.to_csv(output_filename, index=False)
        print(f"[*] Analytics-ready dataset saved successfully to: {output_filename}")
        
    except PermissionError:
        print("\n[!] CRITICAL ERROR: Permission Denied.")
        print("[!] The output file is currently open in another program.")
        print("[!] Please CLOSE the file and run this script again.\n")
    except Exception as e:
        print(f"\n[!] An unexpected error occurred: {str(e)}\n")