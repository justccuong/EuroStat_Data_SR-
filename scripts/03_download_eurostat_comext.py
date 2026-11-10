"""
Script 03: Batch Download Eurostat Comext Dataset DS-059334
Dataset: Extra-EU trade since 2002 by mode of transport, by HS2-4-6
Scope: 509 HS4 codes x 28 reporters (EU27 + EU aggregate) x 36 months (2022M01-2024M12)
Protocol: Eurostat Comext SDMX 2.1 REST API
"""

import urllib.request
import os
import time
import hashlib
import json
import pandas as pd

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "raw_data", "eurostat")
    manifest_dir = os.path.join(base_dir, "manifests")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(manifest_dir, exist_ok=True)

    common_hs4 = pd.read_csv(os.path.join(base_dir, "common_hs4_eu_japan_newzealand_2022.csv"))
    hs4_list = [f"{int(x):04d}" for x in sorted(common_hs4['product'].unique())]
    print(f"Loaded {len(hs4_list)} target HS4 codes.")

    manifest_file = os.path.join(raw_dir, "manifest_eurostat.json")
    if os.path.exists(manifest_file):
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = []
    manifest_dict = {m['batch']: m for m in manifest}

    BATCH_SIZE = 15
    batches = [hs4_list[i:i + BATCH_SIZE] for i in range(0, len(hs4_list), BATCH_SIZE)]
    print(f"Total batches: {len(batches)}")

    for idx, b_codes in enumerate(batches, 1):
        batch_file = os.path.join(raw_dir, f"batch_{idx:03d}.csv")
        prod_query = "+".join(b_codes)
        url = (
            f"https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-059334/"
            f"M..VN.{prod_query}.1..VALUE_EUR+QUANTITY_KG"
            f"?startPeriod=2022-01&endPeriod=2024-12&format=sdmx-csv"
        )

        if os.path.exists(batch_file) and os.path.getsize(batch_file) > 1000:
            print(f"[{idx:02d}/{len(batches)}] Batch {idx} already exists ({os.path.getsize(batch_file)} bytes). Skipping.")
            continue

        print(f"[{idx:02d}/{len(batches)}] Downloading batch {idx} ({len(b_codes)} codes)...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NCKH Study)'})

        success = False
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                with open(batch_file, "wb") as f:
                    f.write(data)
                sha256 = hashlib.sha256(data).hexdigest()
                manifest_dict[idx] = {
                    "batch": idx,
                    "dataset": "DS-059334",
                    "codes": b_codes,
                    "file_name": os.path.basename(batch_file),
                    "file_size_bytes": len(data),
                    "sha256": sha256,
                    "url": url,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                success = True
                print(f"  Saved {len(data)} bytes, sha256={sha256[:10]}...")
                break
            except Exception as e:
                print(f"  Attempt {attempt} failed: {e}")
                time.sleep(3 * attempt)

        if not success:
            print(f"  ERROR: Could not download batch {idx}")
            break
        time.sleep(1.2)

    manifest_list = list(manifest_dict.values())
    for m_path in [manifest_file, os.path.join(manifest_dir, "manifest_eurostat.json")]:
        with open(m_path, "w", encoding="utf-8") as f:
            json.dump(manifest_list, f, indent=2)
    print("Manifest updated successfully.")

if __name__ == "__main__":
    main()
