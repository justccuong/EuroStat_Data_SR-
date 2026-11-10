"""
Script 01: Download ECB Reference Exchange Rates (JPY and NZD against EUR)
Period: 2022-01 to 2024-12 (Monthly)
Source: European Central Bank Data Portal (EXR dataset)
"""

import urllib.request
import ssl
import hashlib
import os
import pandas as pd

def main():
    ctx = ssl._create_unverified_context()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base_dir, "raw_data", "ecb")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ecb_exr_jpy_nzd_eur_2022_2024.csv")

    url = "https://data-api.ecb.europa.eu/service/data/EXR/M.JPY+NZD.EUR.SP00.A?startPeriod=2022-01&endPeriod=2024-12&format=csvdata"
    print(f"Downloading ECB rates from: {url}")
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NCKH Study)'})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = resp.read()

    with open(out_path, "wb") as f:
        f.write(data)

    sha256 = hashlib.sha256(data).hexdigest()
    print(f"Successfully saved {out_path} ({len(data)} bytes, SHA-256: {sha256})")

    df = pd.read_csv(out_path)
    print("Downloaded currencies:", df['CURRENCY'].unique())
    print("Time periods count:", df['TIME_PERIOD'].nunique())

if __name__ == "__main__":
    main()
