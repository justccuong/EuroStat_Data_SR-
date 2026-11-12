"""
Script 04: Build Unified Master Panel Dataset for Stata and Excel
Harmonizes Eurostat EU27 and Stats NZ data across 509 HS4 codes x 36 months (2022M01-2024M12).
Calculates:
- S1_sea_2022: Share of sea transport in 2022 import value at EU border
- S2_lnkgeur_2022: ln(total kg 2022 / total CIF EUR 2022)
- Post: 0 for 1/2022-10/2023, 1 for 1/2024-12/2024
- Excl_1112_2023: 1 for months 11 and 12 of 2023 (exclusion window)
- in_sample: 1 if Excl_1112_2023 == 0 and Status == 'positive'
- EUxPostxS1 and EUxPostxS2: Primary interaction terms
- kg_per_EUR_obs: kg / CIF_EUR (inverse of EUR/kg unit value)
"""

import os
import glob
import numpy as np
import pandas as pd

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_euro_dir = os.path.join(base_dir, "raw_data", "eurostat")
    nz_processed = os.path.join(base_dir, "processed_data", "nz_monthly_509_2022_2024.csv")
    common_hs4_path = os.path.join(base_dir, "common_hs4_eu_japan_newzealand_2022.csv")
    out_dir = os.path.join(base_dir, "processed_data")
    os.makedirs(out_dir, exist_ok=True)

    common_hs4 = pd.read_csv(common_hs4_path)
    target_codes = set([f"{int(x):04d}" for x in common_hs4['product']])
    print(f"Target HS4 count: {len(target_codes)}")

    EU_COUNTRY_MAP = {
        'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'CY': 'Cyprus',
        'CZ': 'Czechia', 'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia',
        'ES': 'Spain', 'FI': 'Finland', 'FR': 'France', 'GR': 'Greece',
        'HR': 'Croatia', 'HU': 'Hungary', 'IE': 'Ireland', 'IT': 'Italy',
        'LT': 'Lithuania', 'LU': 'Luxembourg', 'LV': 'Latvia', 'MT': 'Malta',
        'NL': 'Netherlands', 'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania',
        'SE': 'Sweden', 'SI': 'Slovenia', 'SK': 'Slovakia', 'EU': 'EU27 (Total)'
    }

    euro_files = sorted(glob.glob(os.path.join(raw_euro_dir, "batch_*.csv")))
    print(f"Found {len(euro_files)} Eurostat batch files.")

    dfs = []
    for f in euro_files:
        df_b = pd.read_csv(f, dtype={'product': str, 'transport_mode': str, 'reporter': str})
        dfs.append(df_b)

    df_euro = pd.concat(dfs, ignore_index=True)
    df_euro['product'] = df_euro['product'].astype(str).str.zfill(4)
    df_euro = df_euro[df_euro['product'].isin(target_codes)].copy()
    print(f"Combined Eurostat records in target codes: {len(df_euro)}")

    # Calculate S1 and S2 from 2022 Eurostat data
    df_2022 = df_euro[df_euro['TIME_PERIOD'].str.startswith('2022')].copy()
    hs4_chars = {}

    for code in sorted(list(target_codes)):
        sub = df_2022[df_2022['product'] == code]
        sub_eu = sub[sub['reporter'] == 'EU']
        source_df = sub_eu if not sub_eu.empty else sub[sub['reporter'] != 'EU']

        val_sub = source_df[source_df['indicators'] == 'VALUE_EUR']
        val_tot_2022 = val_sub['OBS_VALUE'].sum()
        val_sea_2022 = val_sub[val_sub['transport_mode'] == '1']['OBS_VALUE'].sum()

        kg_sub = source_df[source_df['indicators'] == 'QUANTITY_KG']
        kg_tot_2022 = kg_sub['OBS_VALUE'].sum()

        s1 = (val_sea_2022 / val_tot_2022) if val_tot_2022 > 0 else 0.0
        s2 = np.log(kg_tot_2022 / val_tot_2022) if (kg_tot_2022 > 0 and val_tot_2022 > 0) else np.nan

        hs4_chars[code] = {
            'HS4': code,
            'S1_sea_2022': round(float(s1), 4),
            'S2_lnkgeur_2022': round(float(s2), 4) if pd.notnull(s2) else np.nan,
            'val_tot_2022_eur': val_tot_2022,
            'val_sea_2022_eur': val_sea_2022,
            'kg_tot_2022': kg_tot_2022
        }

    df_hs4_chars = pd.DataFrame(list(hs4_chars.values()))
    out_hs4_path = os.path.join(out_dir, "HS4_2022_characteristics.csv")
    df_hs4_chars.to_csv(out_hs4_path, index=False)

    # Monthly aggregation
    df_euro['Year'] = df_euro['TIME_PERIOD'].str[:4].astype(int)
    df_euro['Month'] = df_euro['TIME_PERIOD'].str[5:7].astype(int)

    grouped = df_euro.groupby(['product', 'reporter', 'Year', 'Month', 'indicators'])['OBS_VALUE'].sum().unstack('indicators').reset_index()

    panel_records = []
    for _, row in grouped.iterrows():
        code = row['product']
        rep = row['reporter']
        y = int(row['Year'])
        m = int(row['Month'])

        cif_eur = row.get('VALUE_EUR', np.nan)
        kg_val = row.get('QUANTITY_KG', np.nan)
        market_name = EU_COUNTRY_MAP.get(rep, rep)

        c_chars = hs4_chars.get(code, {})
        s1 = c_chars.get('S1_sea_2022', np.nan)
        s2 = c_chars.get('S2_lnkgeur_2022', np.nan)

        if y == 2022 or (y == 2023 and m <= 10):
            post, excl = 0, 0
        elif y == 2023 and m in [11, 12]:
            post, excl = 0, 1
        else:
            post, excl = 1, 0

        status = 'positive' if pd.notnull(cif_eur) and cif_eur > 0 else 'reported_zero'
        ln_cif = np.log(cif_eur) if pd.notnull(cif_eur) and cif_eur > 0 else np.nan
        in_sample = 1 if (excl == 0 and status == 'positive') else 0

        eux_post_s1 = 1 * post * s1 if pd.notnull(s1) else np.nan
        eux_post_s2 = 1 * post * s2 if pd.notnull(s2) else np.nan
        kg_per_eur = (kg_val / cif_eur) if (pd.notnull(kg_val) and pd.notnull(cif_eur) and cif_eur > 0) else np.nan

        panel_records.append({
            'HS4': code, 'Market': market_name, 'Group': 'EU', 'Year': y, 'Month': m,
            'EU': 1, 'Post': post, 'Excl_1112_2023': excl, 'Status': status,
            'CIF_EUR': cif_eur, 'KG': kg_val, 'Currency_goc': 'EUR',
            'S1_sea_2022': s1, 'S2_lnkgeur_2022': s2, 'ln_CIF': ln_cif,
            'in_sample': in_sample, 'EUxPostxS1': eux_post_s1, 'EUxPostxS2': eux_post_s2,
            'kg_per_EUR_obs': kg_per_eur
        })

    # New Zealand integration
    if os.path.exists(nz_processed):
        df_nz = pd.read_csv(nz_processed)
        for _, row in df_nz.iterrows():
            code = str(row['HS4']).zfill(4)
            y = int(row['Year'])
            m = int(row['Month'])
            cif_eur = row['CIF_EUR']
            kg_val = row['KG']

            c_chars = hs4_chars.get(code, {})
            s1 = c_chars.get('S1_sea_2022', np.nan)
            s2 = c_chars.get('S2_lnkgeur_2022', np.nan)

            if y == 2022 or (y == 2023 and m <= 10):
                post, excl = 0, 0
            elif y == 2023 and m in [11, 12]:
                post, excl = 0, 1
            else:
                post, excl = 1, 0

            status = 'positive' if pd.notnull(cif_eur) and cif_eur > 0 else 'reported_zero'
            ln_cif = np.log(cif_eur) if pd.notnull(cif_eur) and cif_eur > 0 else np.nan
            in_sample = 1 if (excl == 0 and status == 'positive') else 0

            eux_post_s1 = 0.0
            eux_post_s2 = 0.0
            kg_per_eur = (kg_val / cif_eur) if (pd.notnull(kg_val) and pd.notnull(cif_eur) and cif_eur > 0) else np.nan

            panel_records.append({
                'HS4': code, 'Market': 'New Zealand', 'Group': 'Comparison', 'Year': y, 'Month': m,
                'EU': 0, 'Post': post, 'Excl_1112_2023': excl, 'Status': status,
                'CIF_EUR': cif_eur, 'KG': kg_val, 'Currency_goc': 'NZD',
                'S1_sea_2022': s1, 'S2_lnkgeur_2022': s2, 'ln_CIF': ln_cif,
                'in_sample': in_sample, 'EUxPostxS1': eux_post_s1, 'EUxPostxS2': eux_post_s2,
                'kg_per_EUR_obs': kg_per_eur
            })

    # Japan integration
    jp_processed = os.path.join(base_dir, "processed_data", "japan_monthly_509_2022_2024.csv")
    if os.path.exists(jp_processed):
        df_jp = pd.read_csv(jp_processed)
        print(f"Integrating Japan monthly data: {len(df_jp)} records...")
        for _, row in df_jp.iterrows():
            code = str(row['HS4']).zfill(4)
            y = int(row['Year'])
            m = int(row['Month'])
            cif_eur = row['CIF_EUR']
            kg_val = row['KG']

            c_chars = hs4_chars.get(code, {})
            s1 = c_chars.get('S1_sea_2022', np.nan)
            s2 = c_chars.get('S2_lnkgeur_2022', np.nan)

            if y == 2022 or (y == 2023 and m <= 10):
                post, excl = 0, 0
            elif y == 2023 and m in [11, 12]:
                post, excl = 0, 1
            else:
                post, excl = 1, 0

            status = 'positive' if pd.notnull(cif_eur) and cif_eur > 0 else 'reported_zero'
            ln_cif = np.log(cif_eur) if pd.notnull(cif_eur) and cif_eur > 0 else np.nan
            in_sample = 1 if (excl == 0 and status == 'positive') else 0

            eux_post_s1 = 0.0
            eux_post_s2 = 0.0
            kg_per_eur = (kg_val / cif_eur) if (pd.notnull(kg_val) and pd.notnull(cif_eur) and cif_eur > 0) else np.nan

            panel_records.append({
                'HS4': code, 'Market': 'Japan', 'Group': 'Comparison', 'Year': y, 'Month': m,
                'EU': 0, 'Post': post, 'Excl_1112_2023': excl, 'Status': status,
                'CIF_EUR': cif_eur, 'KG': kg_val, 'Currency_goc': 'JPY',
                'S1_sea_2022': s1, 'S2_lnkgeur_2022': s2, 'ln_CIF': ln_cif,
                'in_sample': in_sample, 'EUxPostxS1': eux_post_s1, 'EUxPostxS2': eux_post_s2,
                'kg_per_EUR_obs': kg_per_eur
            })

    df_panel = pd.DataFrame(panel_records)
    print(f"Total Combined Panel rows: {len(df_panel)}")

    # Exports
    dta_path = os.path.join(out_dir, "master_panel_stata.dta")
    df_panel.to_stata(dta_path, write_index=False)
    print(f"Exported: {dta_path}")

    csv_path = os.path.join(out_dir, "master_panel.csv")
    df_panel.to_csv(csv_path, index=False)
    print(f"Exported: {csv_path}")

    xlsx_path = os.path.join(out_dir, "master_panel.xlsx")
    try:
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df_panel.iloc[:50000].to_excel(writer, sheet_name="Panel_Sample_50k", index=False)
            df_hs4_chars.to_excel(writer, sheet_name="HS4_2022_Chars", index=False)
        print(f"Exported: {xlsx_path}")
    except Exception as e:
        print(f"Notice (master_panel.xlsx): {e}")

    xlsx_full_path = os.path.join(out_dir, "master_panel_full.xlsx")
    try:
        with pd.ExcelWriter(xlsx_full_path, engine='openpyxl') as writer:
            df_panel.to_excel(writer, sheet_name="Panel_Full", index=False)
            df_hs4_chars.to_excel(writer, sheet_name="HS4_2022_Chars", index=False)
        print(f"Exported: {xlsx_full_path}")
    except Exception as e:
        print(f"Notice (master_panel_full.xlsx): {e}")

if __name__ == "__main__":
    main()
