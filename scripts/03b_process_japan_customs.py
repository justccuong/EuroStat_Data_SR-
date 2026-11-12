import os
import urllib.request
import csv
import io
import json
import hashlib
import pandas as pd
import numpy as np

base_dir = r"e:\Ly_Docs\1 another nc"
raw_japan_dir = os.path.join(base_dir, "raw_data", "japan")
os.makedirs(raw_japan_dir, exist_ok=True)
manifest_dir = os.path.join(base_dir, "manifests")
os.makedirs(manifest_dir, exist_ok=True)

# 1. Load ECB exchange rates
ecb_file = os.path.join(base_dir, "raw_data", "ecb", "ecb_exr_jpy_nzd_eur_2022_2024.csv")
df_ecb = pd.read_csv(ecb_file)
df_jpy_rates = df_ecb[df_ecb['CURRENCY'] == 'JPY'].copy()
df_jpy_rates['Year'] = pd.to_datetime(df_jpy_rates['TIME_PERIOD']).dt.year
df_jpy_rates['Month'] = pd.to_datetime(df_jpy_rates['TIME_PERIOD']).dt.month
jpy_rates = df_jpy_rates.set_index(['Year', 'Month'])['OBS_VALUE'].to_dict()

# 2. Load 509 target HS4 codes
hs4_file = os.path.join(base_dir, "common_hs4_eu_japan_newzealand_2022.csv")
with open(hs4_file, 'r', encoding='utf-8') as f:
    target_hs4 = set(line.strip().zfill(4) for line in f if line.strip())
print(f"Loaded {len(target_hs4)} target HS4 codes.")

# URLs for Japan e-Stat
years_info = [
    (2022, "000040117476", "import_asia_2022.csv"),
    (2023, "000040223264", "import_asia_2023.csv"),
    (2024, "000040368888", "import_asia_2024.csv")
]

manifest_entries = []
all_records = []

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

for year, stat_infid, fname in years_info:
    url = f"https://www.e-stat.go.jp/en/stat-search/file-download?statInfId={stat_infid}&fileKind=1"
    fpath = os.path.join(raw_japan_dir, fname)
    
    if not os.path.exists(fpath):
        print(f"Downloading {year} from {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_bytes = resp.read()
        with open(fpath, "wb") as f_out:
            f_out.write(content_bytes)
        print(f"Saved {fname} ({len(content_bytes)} bytes).")
    else:
        print(f"File {fname} already exists locally.")
        with open(fpath, "rb") as f_in:
            content_bytes = f_in.read()
            
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()
    manifest_entries.append({
        "year": year,
        "filename": fname,
        "source": "Japan Ministry of Finance / e-Stat (Trade Statistics of Japan)",
        "url": url,
        "sha256": sha256_hash,
        "bytes": len(content_bytes)
    })
    
    # Parse CSV content
    text = content_bytes.decode('shift_jis', errors='ignore')
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    
    hs_idx = header.index('HS')
    country_idx = header.index('Country')
    u1_idx = header.index('Unit1')
    u2_idx = header.index('Unit2')
    
    # Process rows
    for r in reader:
        if len(r) <= country_idx or r[country_idx].strip() != '110':
            continue
            
        hs_raw = r[hs_idx].strip().strip("' ")
        hs4 = hs_raw[:4].zfill(4)
        if hs4 not in target_hs4:
            continue
            
        u1 = r[u1_idx].strip()
        u2 = r[u2_idx].strip()
        
        for m_idx, m_name in enumerate(months, start=1):
            val_col = f"Value-{m_name}"
            q1_col = f"Quantity1-{m_name}"
            q2_col = f"Quantity2-{m_name}"
            
            val_idx = header.index(val_col)
            q1_idx = header.index(q1_col)
            q2_idx = header.index(q2_col)
            
            val_str = r[val_idx].strip()
            q1_str = r[q1_idx].strip()
            q2_str = r[q2_idx].strip()
            
            val_thousand_jpy = float(val_str) if val_str else 0.0
            q1 = float(q1_str) if q1_str else 0.0
            q2 = float(q2_str) if q2_str else 0.0
            
            # Convert weight to KG
            kg = 0.0
            if u2 == 'KG':
                kg = q2
            elif u2 == 'MT':
                kg = q2 * 1000.0
            elif u2 == 'GR':
                kg = q2 * 0.001
            elif u1 == 'KG':
                kg = q1
            elif u1 == 'MT':
                kg = q1 * 1000.0
            elif u1 == 'GR':
                kg = q1 * 0.001
                
            val_jpy = val_thousand_jpy * 1000.0
            
            if val_jpy > 0 or kg > 0:
                all_records.append({
                    'HS4': hs4,
                    'Year': year,
                    'Month': m_idx,
                    'Value_JPY': val_jpy,
                    'KG': kg
                })

df_raw_jp = pd.DataFrame(all_records)
print(f"Total raw records matched: {len(df_raw_jp)}")

# Aggregate by HS4 x Year x Month
df_agg = df_raw_jp.groupby(['HS4', 'Year', 'Month'], as_index=False).agg({
    'Value_JPY': 'sum',
    'KG': 'sum'
})
print(f"Aggregated records (HS4 x Year x Month): {len(df_agg)}")

# Map ECB rate and calculate CIF_EUR
def get_rate(row):
    return jpy_rates.get((row['Year'], row['Month']), np.nan)

df_agg['exr_jpy_eur'] = df_agg.apply(get_rate, axis=1)
df_agg['CIF_EUR'] = df_agg['Value_JPY'] / df_agg['exr_jpy_eur']

# Save Japan monthly processed file
out_jp_csv = os.path.join(base_dir, "processed_data", "japan_monthly_509_2022_2024.csv")
df_agg.to_csv(out_jp_csv, index=False)
print(f"Saved: {out_jp_csv}")

# Save manifest
manifest_path = os.path.join(manifest_dir, "manifest_japan.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest_entries, f, indent=2)
print(f"Saved manifest: {manifest_path}")

print("Summary:")
print(f"Unique HS4: {df_agg['HS4'].nunique()} / {len(target_hs4)}")
print(f"Total CIF EUR: {df_agg['CIF_EUR'].sum():,.2f}")
print(f"Sample data:")
print(df_agg.head(10))
