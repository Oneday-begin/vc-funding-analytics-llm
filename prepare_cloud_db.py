"""Restore the interview database from the committed, cleaned seed on each restart."""
import gzip
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def prepare(path="cloud.db"):
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS startup_investments (
            id INTEGER PRIMARY KEY, name TEXT, market TEXT, funding_total_usd REAL,
            status TEXT, country_code TEXT, founded_year INTEGER)""")
        if not conn.execute("SELECT COUNT(*) FROM startup_investments").fetchone()[0]:
            with gzip.open(Path(__file__).parent / "data" / "investments.json.gz", "rt", encoding="utf-8") as f:
                records = json.load(f)
            conn.executemany("""INSERT INTO startup_investments
                (name, market, funding_total_usd, status, country_code, founded_year)
                VALUES (?, ?, ?, ?, ?, ?)""", records)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_market ON startup_investments(market)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_country ON startup_investments(country_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON startup_investments(founded_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_funding ON startup_investments(funding_total_usd)")
        conn.execute("""CREATE TABLE IF NOT EXISTS ai_due_diligence_summaries (
            startup_id INTEGER PRIMARY KEY, startup_name TEXT, market TEXT,
            funding_tier TEXT, maturity_stage TEXT, country_code TEXT,
            investment_thesis TEXT, model_used TEXT, generated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        print("Cloud database ready:", conn.execute("SELECT COUNT(*) FROM startup_investments").fetchone()[0], "startups")


if __name__ == "__main__":
    prepare()
