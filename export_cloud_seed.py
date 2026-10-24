"""Export public investment fields using the same cleaning as the MySQL ETL."""
import argparse
import gzip
import json
from pathlib import Path

import pandas as pd
from etl_pipeline import clean_chunk, CSV_ENCODING


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    rows = []
    columns = ["name", "market", "funding_total_usd", "status", "country_code", "founded_year"]
    for raw in pd.read_csv(args.csv, encoding=CSV_ENCODING, chunksize=5000, low_memory=False):
        cleaned = clean_chunk(raw)[columns]
        rows.extend(json.loads(cleaned.to_json(orient="values")))
    target = Path(__file__).parent / "data" / "investments.json.gz"
    target.parent.mkdir(exist_ok=True)
    with target.open("wb") as f:
        f.write(gzip.compress(json.dumps(rows, ensure_ascii=False, allow_nan=False).encode("utf-8"), mtime=0))
    print(f"Exported {len(rows)} cleaned records ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
