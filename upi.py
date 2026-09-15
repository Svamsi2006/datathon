import pandas as pd
import numpy as np
import re
import warnings

# Suppress pandas chained assignment warnings for cleaner output
warnings.filterwarnings('ignore')

class UPITransactionOptimizer:
    """
    A rigorous, non-destructive data engineering pipeline for track1_upi_transactions.csv.
    Designed to prepare financial ledgers for fraud ring detection and merchant risk analytics.
    Features:
    - Triple-Key Regex Normalization (txn_id, user_id, merchant_id)
    - Financial Value Sanitization (Regex extraction + absolute value correction)
    - Status Consolidation (SUCCESS, FAILED, PENDING)
    - UTR Fraud Flagging (Missing UTR Boolean)
    - Smart Survivorship Deduplication
    """
    
    def __init__(self, file_path):
        try:
            self.df = pd.read_csv(file_path)
            self.initial_rows = len(self.df)
            # Ensure standard column names exist (handling potential typos in raw data)
            self.df.columns = self.df.columns.str.lower().str.strip()
            print(f"[*] Successfully loaded UPI Dataset. Initial row count: {self.initial_rows}")
        except FileNotFoundError:
            raise Exception(f"CRITICAL ERROR: {file_path} not found. Ensure the file is in the directory.")

    def deep_data_profiling(self):
        """
        Simulates human EDA. Fetches top unique values for critical transaction columns
        to understand the noise topology before automated cleaning rules are applied.
        """
        print("\n" + "="*55)
        print("HUMAN-LIKE EDA: DEEP COLUMN PROFILING (UPI TRANSACTIONS)")
        print("="*55)
        
        # Look for standard column names, falling back gracefully if exact name varies
        cols_to_profile = [col for col in ['transaction_status', 'status', 'utr_number', 'utr', 'amount', 'transaction_amount'] if col in self.df.columns]
        
        for col in cols_to_profile:
            print(f"\n--- Analyzing Column: '{col}' ---")
            top_values = self.df[col].value_counts(dropna=False).head(10)
            for val, count in top_values.items():
                print(f"  -> {str(val).ljust(25)} : {count} occurrences")
                
        print("\n[*] Profiling complete. Pipeline will execute targeted normalizations...\n")

    def normalize_keys(self):
        """
        Critical Step: If user_id or merchant_id formats don't perfectly match their 
        respective master tables, SQL joins will drop rows.
        Standardizes to: USR12345, MCH1234, TXN987654.
        """
        print("[*] Normalizing Primary/Foreign Keys (txn_id, user_id, merchant_id)...")
        
        def clean_id(val, prefix):
            if pd.isna(val) or str(val).lower() == 'nan':
                return f'UNKNOWN_{prefix}'
            # Uppercase and strip non-alphanumerics (removes hyphens, spaces, underscores)
            val = re.sub(r'[^A-Z0-9]', '', str(val).upper())
            
            # If the ID is just digits (e.g. '12345'), prepend the correct prefix
            if val.isdigit():
                return f'{prefix}{val}'
            
            # Fix lowercase prefixes (e.g. 'usr123' -> 'USR123' handled by upper(), but ensure no weird duplicates)
            return val

        # 1. Transaction ID
        if 'txn_id' in self.df.columns:
            self.df['txn_id_clean'] = self.df['txn_id'].apply(lambda x: clean_id(x, 'TXN'))
        elif 'transaction_id' in self.df.columns:
            self.df['txn_id_clean'] = self.df['transaction_id'].apply(lambda x: clean_id(x, 'TXN'))

        # 2. User ID (Foreign Key to KYC Table)
        if 'user_id' in self.df.columns:
            self.df['user_id_clean'] = self.df['user_id'].apply(lambda x: clean_id(x, 'USR'))
            
        # 3. Merchant ID (Foreign Key to Merchant Table)
        if 'merchant_id' in self.df.columns:
            self.df['merchant_id_clean'] = self.df['merchant_id'].apply(lambda x: clean_id(x, 'MCH'))

    def normalize_status(self):
        """
        Collapses messy user-entered or system-generated statuses into 3 strict states:
        SUCCESS, FAILED, PENDING.
        """
        print("[*] Consolidating Transaction Statuses...")
        status_col = 'transaction_status' if 'transaction_status' in self.df.columns else 'status'
        
        if status_col in self.df.columns:
            def map_status(val):
                if pd.isna(val): return 'UNKNOWN'
                # Aggressively clean: remove punctuation, strip whitespace, uppercase
                val_upper = re.sub(r'[^A-Za-z]', '', str(val)).strip().upper()
                
                # Success variants (Explicitly maps single letter 'S')
                if val_upper in ['SUCCESS', 'TXNSUCCESS', 'COMPLETED', 'DONE', 'S', 'Y', 'YES']:
                    return 'SUCCESS'
                # Failed variants (Explicitly maps single letter 'F')
                elif val_upper in ['FAILED', 'FAIL', 'DECLINED', 'REJECTED', 'F', 'ERROR', 'N', 'NO']:
                    return 'FAILED'
                # Pending variants (Explicitly maps single letter 'P')
                elif val_upper in ['PENDING', 'PROCESSING', 'INITIATED', 'P', 'W', 'WAITING']:
                    return 'PENDING'
                
                return 'UNKNOWN' # Failsafe for complete anomalies
                
            self.df['status_clean'] = self.df[status_col].apply(map_status)

    def clean_utr_and_flags(self):
        """
        UTR (Unique Transaction Reference) is crucial for tracing payments. 
        Missing UTRs on 'SUCCESS' transactions are massive fraud indicators.
        We will clean the string and generate an explicit boolean flag for the AI Agent.
        """
        print("[*] Sanitizing UTRs and Generating Fraud Telemetry Flags...")
        utr_col = 'utr_number' if 'utr_number' in self.df.columns else 'utr'
        
        if utr_col in self.df.columns:
            # 1. Structural Validation: Strip hyphens, spaces
            self.df['utr_clean'] = self.df[utr_col].astype(str).str.replace(r'[^A-Za-z0-9]', '', regex=True)
            self.df['utr_clean'] = self.df['utr_clean'].replace(['NAN', ''], np.nan)
            
            # 2. Fraud Engineering: Flag missing UTRs
            self.df['is_missing_utr'] = self.df['utr_clean'].isna()
            
            # 3. Safe Imputation
            self.df['utr_clean'].fillna('UNAVAILABLE', inplace=True)

    def parse_financials(self):
        """
        Extracts numbers from messy strings (e.g., 'Rs. 1,500.50', '₹-400').
        Mathematically corrects invalid negative transactions.
        """
        print("[*] Parsing Financial Vectors (Amount Extraction)...")
        amt_col = 'transaction_amount' if 'transaction_amount' in self.df.columns else 'amount'
        
        if amt_col in self.df.columns:
            def clean_amount(val):
                if pd.isna(val): return np.nan
                # Keep digits, decimals, and negative signs. Strip commas and letters.
                cleaned_str = re.sub(r'[^\d\.-]', '', str(val))
                try:
                    # float() parses the string. abs() corrects accidental negative inputs 
                    # (a transaction amount in a ledger should be absolute; direction is handled by Dr/Cr)
                    return abs(float(cleaned_str))
                except ValueError:
                    return np.nan
                    
            self.df['amount_clean'] = self.df[amt_col].apply(clean_amount)
            
            # Contextual Imputation: Fill missing amounts with the median of that specific User
            if 'user_id_clean' in self.df.columns:
                self.df['amount_clean'] = self.df.groupby('user_id_clean')['amount_clean'].transform(
                    lambda x: x.fillna(x.median())
                )
            # Failsafe global median if still NaN
            global_median = self.df['amount_clean'].median()
            self.df['amount_clean'].fillna(global_median, inplace=True)
            
            # Enforce strict 2-decimal uniform format for all amounts
            self.df['amount_clean'] = self.df['amount_clean'].round(2)

    def parse_temporal(self):
        """
        Standardizes timestamps for time-series forecasting. Handles Unix epochs.
        """
        print("[*] Normalizing Temporal Timestamps...")
        date_col = 'timestamp' if 'timestamp' in self.df.columns else ('transaction_date' if 'transaction_date' in self.df.columns else None)
        
        if date_col:
            # 1. Identify valid numeric epochs
            is_epoch = pd.to_numeric(self.df[date_col], errors='coerce').notna() & (self.df[date_col].astype(str).str.len() == 10)
            
            # 2. Initialize a blank datetime series
            parsed_dates = pd.Series(index=self.df.index, dtype='datetime64[ns]')
            
            # 3. Parse epochs
            if is_epoch.any():
                parsed_dates[is_epoch] = pd.to_datetime(self.df[date_col][is_epoch].astype(int), unit='s')
                
            # 4. Parse mixed strings
            if (~is_epoch).any():
                # We remove mixed=True to ensure pandas version compatibility, it infers automatically
                parsed_dates[~is_epoch] = pd.to_datetime(self.df[date_col][~is_epoch], errors='coerce')
                
            self.df['timestamp_clean'] = parsed_dates
            
            # Format explicitly to YYYY-MM-DD HH:MM:SS to unify all timestamps
            self.df['timestamp_clean'] = self.df['timestamp_clean'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            self.df['has_valid_timestamp'] = self.df['timestamp_clean'].notna()

    def smart_deduplication(self):
        """
        Applies Smart Survivorship: groups by txn_id, scores rows by data completeness,
        and retains the richest row.
        """
        if 'txn_id_clean' not in self.df.columns:
            return
            
        print("[*] Executing Smart Survivorship Deduplication...")
        
        # Calculate 'data richness'
        self.df['non_null_count'] = self.df.notna().sum(axis=1)
        
        # Sort by primary key, then richness (descending), then timestamp (newest)
        sort_cols = ['txn_id_clean', 'non_null_count']
        asc_flags = [True, False]
        
        if 'timestamp_clean' in self.df.columns:
            sort_cols.append('timestamp_clean')
            asc_flags.append(False)
            
        self.df = self.df.sort_values(by=sort_cols, ascending=asc_flags)
        
        # Drop duplicates, keeping the first (richest) row
        self.df = self.df.drop_duplicates(subset=['txn_id_clean'], keep='first')
        
        # Cleanup
        self.df.drop(columns=['non_null_count'], inplace=True)
        self.final_rows = len(self.df)

    def execute(self):
        """
        Runs the full execution trace and exports the target dataframe.
        """
        self.deep_data_profiling()
        self.normalize_keys()
        self.normalize_status()
        self.clean_utr_and_flags()
        self.parse_financials()
        self.parse_temporal()
        self.smart_deduplication()
        
        # Map back to clean, expected column names
        col_mapping = {
            'txn_id_clean': 'txn_id',
            'user_id_clean': 'user_id',
            'merchant_id_clean': 'merchant_id',
            'amount_clean': 'transaction_amount',
            'status_clean': 'transaction_status',
            'utr_clean': 'utr_number',
            'is_missing_utr': 'is_missing_utr',           # Fraud Feature
            'timestamp_clean': 'timestamp',
            'has_valid_timestamp': 'has_valid_timestamp'  # Fraud Feature
        }
        
        target_cols = [col for col in col_mapping.keys() if col in self.df.columns]
        self.df = self.df[target_cols]
        self.df.rename(columns={k: col_mapping[k] for k in target_cols}, inplace=True)
        
        print("\n=== UPI PIPELINE EXECUTION SUMMARY ===")
        print(f"Initial Raw Transactions: {self.initial_rows}")
        print(f"Final Deduplicated Transactions: {self.final_rows}")
        print("Architectural Enhancements: Missing UTR Flagging, Negative Balance Rectification, Triple-Key Normalization.")
        print("======================================\n")
        
        return self.df

# --- Entry Point ---
if __name__ == "__main__":
    # Wrap in a try-except block to gracefully handle Windows file locks
    try:
        pipeline = UPITransactionOptimizer('track1_upi_transactions.csv')
        cleaned_upi_df = pipeline.execute()
        
        output_filename = 'updated_upi.csv'
        cleaned_upi_df.to_csv(output_filename, index=False)
        print(f"[*] Analytics-ready dataset saved successfully to: {output_filename}")
        
    except PermissionError:
        print("\n[!] CRITICAL ERROR: Permission Denied.")
        print("[!] The file 'updated_upi.csv' is currently open in Excel or another program.")
        print("[!] Please CLOSE the file and run this script again.\n")
    except Exception as e:
        print(f"\n[!] An unexpected error occurred: {str(e)}\n")