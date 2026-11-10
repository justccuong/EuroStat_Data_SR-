"""
Script 05: Generate Verification & Audit Reports for Supervisor
Creates:
- audit_table_by_market.csv: Observations, published cells, value by country
- audit_table_by_month.csv: Observations and trade values across 36 months
- audit_summary.json: Metadata summary
"""

import os
import json
import pandas as pd

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc_dir = os.path.join(base_dir, "processed_data")
    dta_path = os.path.join(proc_dir, "master_panel_stata.dta")

    df = pd.read_stata(dta_path)

    # By market
    market_audit = df.groupby('Market').agg(
        total_obs=('CIF_EUR', 'count'),
        positive_obs=('Status', lambda x: (x == 'positive').sum()),
        reported_zero=('Status', lambda x: (x == 'reported_zero').sum()),
        total_cif_eur=('CIF_EUR', 'sum'),
        total_kg=('KG', 'sum'),
        in_sample_obs=('in_sample', 'sum'),
        unique_hs4=('HS4', 'nunique')
    ).reset_index()
    market_audit['total_cif_mil_eur'] = market_audit['total_cif_eur'] / 1e6
    market_audit = market_audit.sort_values(by='total_obs', ascending=False)
    market_audit.to_csv(os.path.join(proc_dir, "audit_table_by_market.csv"), index=False)

    # By month
    time_audit = df.groupby(['Year', 'Month', 'Post', 'Excl_1112_2023']).agg(
        total_obs=('CIF_EUR', 'count'),
        positive_obs=('Status', lambda x: (x == 'positive').sum()),
        total_cif_eur=('CIF_EUR', 'sum'),
        in_sample_obs=('in_sample', 'sum')
    ).reset_index()
    time_audit['total_cif_mil_eur'] = time_audit['total_cif_eur'] / 1e6
    time_audit.to_csv(os.path.join(proc_dir, "audit_table_by_month.csv"), index=False)

    # Summary JSON
    summary = {
        "total_panel_rows": len(df),
        "unique_hs4_codes": int(df['HS4'].nunique()),
        "unique_markets": int(df['Market'].nunique()),
        "time_range": "2022-01 to 2024-12 (36 months)",
        "total_positive_cells": int((df['Status'] == 'positive').sum()),
        "total_reported_zero": int((df['Status'] == 'reported_zero').sum()),
        "total_in_sample_cells": int((df['in_sample'] == 1).sum()),
        "markets_list": sorted(list(df['Market'].unique()))
    }
    with open(os.path.join(proc_dir, "audit_summary.json"), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("Audit reports generated successfully!")

if __name__ == "__main__":
    main()
