"""
Script 02: Download and Process New Zealand Overseas Merchandise Trade Data
Period: 2022 to 2024
Source: Stats NZ (Statistics New Zealand)
Extracts Vietnam imports for the fixed 509 HS4 basket and converts NZD to EUR via ECB rates.
"""

import urllib.request
import zipfile
import io
import os
import hashlib
import json
import pandas as pd

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "raw_data", "new_zealand")
    proc_dir = os.path.join(base_dir, "processed_data")
    manifest_dir = os.path.join(base_dir, "manifests")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(proc_dir, exist_ok=True)
    os.makedirs(manifest_dir, exist_ok=True)

    # 1. Target HS4 basket
    common_hs4 = pd.read_csv(os.path.join(base_dir, "common_hs4_eu_japan_newzealand_2022.csv"))
    hs4_set = set([f"{int(x):04d}" for x in common_hs4['product']])
    print(f"Loaded {len(hs4_set)} target HS4 codes.")

    # 2. ECB Exchange rates
    ecb_path = os.path.join(base_dir, "raw_data", "ecb", "ecb_exr_jpy_nzd_eur_2022_2024.csv")
    ecb_df = pd.read_csv(ecb_path)
    nzd_rates = {}
    for _, r in ecb_df[ecb_df['CURRENCY'] == 'NZD'].iterrows():
        nzd_rates[str(r['TIME_PERIOD'])] = float(r['OBS_VALUE'])

    nz_manifest = []
    nz_records = []

    for yr in [2022, 2023, 2024]:
        url = f"https://www3.stats.govt.nz/HS10_by_Country/{yr}_Imports_HS10_by_Country.zip"
        zip_path = os.path.join(raw_dir, f"{yr}_Imports_HS10_by_Country.zip")
        print(f"\nProcessing NZ {yr} from {url}...")

        if not os.path.exists(zip_path):
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NCKH Study)'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            with open(zip_path, "wb") as f:
                f.write(data)
        else:
            with open(zip_path, "rb") as f:
                data = f.read()

        sha256 = hashlib.sha256(data).hexdigest()
        nz_manifest.append({
            "source": "Stats NZ",
            "dataset": f"{yr}_Imports_HS10_by_Country",
            "url": url,
            "file_name": os.path.basename(zip_path),
            "file_size_bytes": len(data),
            "sha256": sha256
        })

        z = zipfile.ZipFile(io.BytesIO(data))
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df_yr = pd.read_csv(f)

        df_vn = df_yr[df_yr['country'] == 'Viet Nam'].copy()
        df_vn['hs4'] = df_vn['hs'].apply(lambda x: str(x).zfill(10)[:4])
        df_vn_target = df_vn[df_vn['hs4'].isin(hs4_set)].copy()

        df_vn_target['year'] = df_vn_target['month'].astype(str).str[:4].astype(int)
        df_vn_target['m'] = df_vn_target['month'].astype(str).str[4:6].astype(int)

        grouped = df_vn_target.groupby(['hs4', 'year', 'm']).agg(
            cif_nzd=('cif', 'sum'),
            qty_sum=('qty', 'sum')
        ).reset_index()

        for _, row in grouped.iterrows():
            hs4_val = row['hs4']
            y_val = int(row['year'])
            m_val = int(row['m'])
            period_str = f"{y_val}-{m_val:02d}"
            cif_nzd_val = float(row['cif_nzd'])
            qty_val = float(row['qty_sum']) if pd.notnull(row['qty_sum']) else None

            rate = nzd_rates.get(period_str)
            cif_eur_val = cif_nzd_val / rate if rate else None

            nz_records.append({
                'HS4': hs4_val,
                'Market': 'New Zealand',
                'Group': 'Comparison',
                'Year': y_val,
                'Month': m_val,
                'EU': 0,
                'CIF_raw': cif_nzd_val,
                'CIF_EUR': cif_eur_val,
                'KG': qty_val,
                'Currency_goc': 'NZD',
                'Status': 'positive' if cif_nzd_val > 0 else 'reported_zero'
            })

    df_nz_all = pd.DataFrame(nz_records)
    out_csv = os.path.join(proc_dir, "nz_monthly_509_2022_2024.csv")
    df_nz_all.to_csv(out_csv, index=False)
    print(f"\nSaved {len(df_nz_all)} aggregated monthly records to {out_csv}")

    for m_path in [os.path.join(raw_dir, "manifest_nz.json"), os.path.join(manifest_dir, "manifest_nz.json")]:
        with open(m_path, "w", encoding="utf-8") as f:
            json.dump(nz_manifest, f, indent=2)

if __name__ == "__main__":
    main()
