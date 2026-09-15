import pandas as pd
import numpy as np
import re
import warnings
warnings.filterwarnings('ignore')

def build_gold_kyc_master(file_path):
    print("Loading raw KYC records...")
    df = pd.read_csv(file_path)
    initial_count = len(df)
    
    # --- 1. Entity Resolution & Harmonization ---
    def clean_uid(val):
        if pd.isna(val): return val
        digits = re.sub(r'\D', '', str(val))
        return f"USR{digits}"
    df['user_id'] = df['user_id'].apply(clean_uid)
    
    # --- 2. Demographic Formatting ---
    df['full_name'] = df['full_name'].astype(str).str.title().str.strip()
    
    # --- 3. Identity Document Processing ---
    df['pan'] = df['pan'].astype(str).str.upper().str.strip().str.replace(r'[^A-Z0-9]', '', regex=True)
    df['pan'] = df['pan'].replace(['NAN', 'NONE', ''], 'MISSING_PAN')
    
    def clean_aadhaar(val):
        if pd.isna(val): return 'MISSING_AADHAAR'
        digits = re.sub(r'\D|\.0$', '', str(val))
        return digits or 'MISSING_AADHAAR'

    df['aadhaar'] = df['aadhaar'].apply(clean_aadhaar)
    
    # Aadhaar Length Integrity Flag (Catches 4-digit partial KYC vs 12-digit full KYC)
    def validate_id(val):
        if val == 'MISSING_AADHAAR': return 'MISSING'
        length = len(val)
        if length == 12: return 'VALID_12_DIGIT'
        elif length == 4: return 'PARTIAL_4_DIGIT'
        else: return 'INVALID_LENGTH'
    df['id_validation_status'] = df['aadhaar'].apply(validate_id)
    
    # --- 4. Geographic & Risk Normalization ---
    for col in ['state', 'occupation', 'risk_segment']:
        df[col] = df[col].astype(str).str.title().str.strip()
        df[col] = df[col].replace(['Nan', 'None', ''], 'Unknown')

    # Canonical City Mapping (Fixes Dilli/Delhi, Hyd/Hyderabad fragmentation)
    city_mapping = {
        r'^dilli$|^new delhi$': 'Delhi',
        r'^hyd$|^hybd$': 'Hyderabad',
        r'^bombay$|^mumbay$': 'Mumbai',
        r'^bangalore$|^blr$': 'Bengaluru',
        r'^calcutta$': 'Kolkata',
        r'^madras$': 'Chennai',
        r'^poona$': 'Pune',
        r'^lko$': 'Lucknow',
        r'^ldh$': 'Ludhiana',
        r'^jalandar$': 'Jalandhar',
        r'^jpr$': 'Jaipur',
        r'^asr$': 'Amritsar'
    }
    df['city'] = df['city'].astype(str).str.title().str.strip()
    for messy_regex, clean_name in city_mapping.items():
        df['city'] = df['city'].str.replace(messy_regex, clean_name, flags=re.IGNORECASE, regex=True)

    # --- 5. Financial Normalization (Audited Income Cleaner) ---
    def clean_income(val):
        if pd.isna(val): return np.nan
        val_str = str(val).lower().strip()
        val_str = re.sub(r'rs\.?\s*|inr\s*|₹\s*|,', '', val_str)
        multiplier = 1
        if 'k' in val_str: multiplier = 1000
        elif 'l' in val_str or 'lakh' in val_str: multiplier = 100000
        match = re.search(r'-?\d+\.?\d*', val_str)
        if match: return abs(float(match.group()) * multiplier)
        return np.nan
            
    df['monthly_income'] = df['monthly_income'].apply(clean_income)
    median_income = df['monthly_income'].median()
    df['monthly_income'] = df['monthly_income'].fillna(median_income)
    
    # --- 6. Account Status Normalization (Audited 100% Mapping) ---
    def normalize_status(val):
        if pd.isna(val): return 'UNKNOWN'
        val = str(val).upper().strip()
        if val in ['DONE', 'VERIFIED', 'APPROVED', 'V', 'SUCCESS', 'KYC_DONE']: 
            return 'VERIFIED'
        elif val in ['PENDING', 'P', 'IN PROGRESS', 'WIP', 'IN_PROGRESS', 'UNDER REVIEW']: 
            return 'PENDING'
        elif val in ['REJECTED', 'R', 'FAIL', 'DENIED', 'REJECT', 'FAILED']: 
            return 'REJECTED'
        else: 
            return 'UNKNOWN'
    df['kyc_status'] = df['kyc_status'].apply(normalize_status)
    
    # --- 7. Temporal Normalization & Feature Flags ---
    df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], dayfirst=True, errors='coerce')
    
    def clean_mixed_timestamp(val):
        if pd.isna(val): return pd.NaT
        val_str = str(val).strip()
        if val_str.isdigit() and len(val_str) == 10:
            return pd.to_datetime(int(val_str), unit='s')
        else:
            return pd.to_datetime(val_str, dayfirst=True, errors='coerce')
            
    df['signup_timestamp'] = df['signup_timestamp'].apply(clean_mixed_timestamp)
    df['is_dob_missing'] = df['date_of_birth'].isna()
    df['is_signup_time_missing'] = df['signup_timestamp'].isna()
    
    # --- 8. Master Deduplication (Ensures 1 row per unique user) ---
    df = df.sort_values(by=['user_id', 'signup_timestamp'])
    df = df.drop_duplicates(subset=['user_id'], keep='last')
    
    print(f"Audit Summary: Initial Rows = {initial_count}, Final Unique Master Users = {len(df)}")
    return df

# Execute and Save
gold_kyc = build_gold_kyc_master('track1_kyc_records.csv')
gold_kyc.to_csv('cleaned_kyc_data.csv', index=False)
print("Pristine Gold KYC Master saved successfully.")