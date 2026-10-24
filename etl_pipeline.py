"""
etl_pipeline.py
================
Production-grade ETL Pipeline for VC Funding Analytics & AI Due Diligence Engine.

Features:
  - Chunked CSV ingestion (chunksize=5000) for memory efficiency
  - Robust data cleaning: type coercion, null handling, encoding normalization
  - Chunked MySQL append ingestion via SQLAlchemy + PyMySQL
  - Structured logging with run-time statistics
"""

import logging
import sys
import time
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CSV_PATH = os.getenv("CSV_PATH", "investments_VC.csv")
CSV_ENCODING = "unicode_escape"
CHUNK_SIZE = 5_000

DB_USER = os.getenv("DB_USER", "root")
# Escape password characters to prevent SQLAlchemy URL parsing errors
DB_PASSWORD = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "vc_analytics_db")
TABLE_NAME = "startup_investments"

# Columns we care about – map raw CSV names → canonical names
COLUMN_MAP = {
    "name":              "name",
    "market":            "market",
    "funding_total_usd": "funding_total_usd",
    "status":            "status",
    "country_code":      "country_code",
    "founded_year":      "founded_year",
    # Optional extras kept when present in the CSV
    "funding_rounds":    "funding_rounds",
    "first_funding_at":  "first_funding_at",
    "last_funding_at":   "last_funding_at",
}

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_pipeline.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────

def build_engine():
    """Create a SQLAlchemy engine with PyMySQL driver."""
    url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(
        url,
        pool_pre_ping=True,        # validate connections before use
        pool_recycle=3600,         # recycle stale connections hourly
        echo=False,
    )
    log.info("SQLAlchemy engine created for database '%s'.", DB_NAME)
    return engine


def ensure_database(engine):
    """Create the target database and table if they don't exist."""
    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (
        id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
        name                VARCHAR(512),
        market              VARCHAR(255),
        funding_total_usd   DOUBLE,
        status              VARCHAR(100),
        country_code        CHAR(10),
        founded_year        SMALLINT,
        funding_rounds      SMALLINT,
        first_funding_at    DATE,
        last_funding_at     DATE,
        inserted_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_market    (market),
        INDEX idx_country   (country_code),
        INDEX idx_year      (founded_year),
        INDEX idx_funding   (funding_total_usd)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    log.info("Table `%s` is ready.", TABLE_NAME)


# ──────────────────────────────────────────────
# Data Cleaning
# ──────────────────────────────────────────────

_FUNDING_STRIP = str.maketrans("", "", ",$+")   # strip commas, dollar signs, plus signs

def clean_funding(series: pd.Series) -> pd.Series:
    """Coerce funding column to float, treating any non-numeric as NaN."""
    s = series.astype(str).str.strip().str.translate(_FUNDING_STRIP)
    s = s.replace({"nan": np.nan, "": np.nan, "-": np.nan, "N/A": np.nan, "None": np.nan})
    return pd.to_numeric(s, errors="coerce")


def clean_year(series: pd.Series) -> pd.Series:
    """Extract 4-digit year, coerce to Int16 nullable integer."""
    s = pd.to_numeric(series.astype(str).str.extract(r"(\d{4})", expand=False), errors="coerce")
    # Sanity-check: VC data reasonably spans 1900–2030
    s = s.where(s.between(1900, 2030))
    return s.astype("Int16")   # nullable integer


def clean_date_col(series: pd.Series) -> pd.Series:
    """Parse date strings to datetime, returning None for unparseable values."""
    return pd.to_datetime(series, errors="coerce")


def normalize_text(series: pd.Series, max_len: int = None) -> pd.Series:
    """Strip whitespace, title-case, and optionally truncate string columns."""
    s = series.astype(str).str.strip()
    s = s.replace({"nan": None, "": None, "None": None})
    if max_len:
        s = s.str[:max_len]
    return s


def clean_chunk(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all cleaning transforms to a raw CSV chunk.
    Returns a DataFrame with only the canonical column set.
    """
    # ── Lowercase all column headers for consistent access
    raw.columns = [c.strip().lower().replace(" ", "_") for c in raw.columns]

    # ── Select only columns we care about (some may be absent)
    available = {k: v for k, v in COLUMN_MAP.items() if k in raw.columns}
    df = raw[list(available.keys())].copy()
    df.rename(columns=available, inplace=True)

    # ── Text columns
    for col in ("name", "market", "status", "country_code"):
        if col in df.columns:
            max_len = 512 if col == "name" else 255
            df[col] = normalize_text(df[col], max_len=max_len)

    # ── Funding
    if "funding_total_usd" in df.columns:
        df["funding_total_usd"] = clean_funding(df["funding_total_usd"])

    # ── Year
    if "founded_year" in df.columns:
        df["founded_year"] = clean_year(df["founded_year"])

    # ── Funding rounds
    if "funding_rounds" in df.columns:
        df["funding_rounds"] = pd.to_numeric(df["funding_rounds"], errors="coerce").astype("Int16")

    # ── Date columns
    for col in ("first_funding_at", "last_funding_at"):
        if col in df.columns:
            df[col] = clean_date_col(df[col])

    # ── Ensure mandatory columns exist (add as NaN if missing from CSV)
    for mandatory in ("name", "market", "funding_total_usd", "status", "country_code", "founded_year"):
        if mandatory not in df.columns:
            df[mandatory] = np.nan

    # ── Drop rows with NO useful signal (no name AND no funding)
    df.dropna(subset=["name", "funding_total_usd"], how="all", inplace=True)

    # ── Reset index per chunk
    df.reset_index(drop=True, inplace=True)

    return df


# ──────────────────────────────────────────────
# ETL Orchestration
# ──────────────────────────────────────────────

def run_etl(csv_path=None):
    source_path = csv_path or CSV_PATH
    start = time.perf_counter()
    log.info("=" * 60)
    log.info("VC Funding ETL Pipeline - START")
    log.info("Source : %s", source_path)
    log.info("Target : %s.%s", DB_NAME, TABLE_NAME)
    log.info("=" * 60)

    # Validate source file
    if not Path(source_path).exists():
        log.error("CSV file not found at: %s", source_path)
        sys.exit(1)

    # Build DB connection
    try:
        engine = build_engine()
        ensure_database(engine)
    except SQLAlchemyError as exc:
        log.error("Database connection failed: %s", exc)
        sys.exit(1)

    # Stream-process CSV in chunks
    total_rows_raw = 0
    total_rows_written = 0
    chunk_num = 0
    skipped_rows = 0

    reader = pd.read_csv(
        source_path,
        encoding=CSV_ENCODING,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        on_bad_lines="warn",
    )

    for raw_chunk in reader:
        chunk_num += 1
        raw_count = len(raw_chunk)
        total_rows_raw += raw_count
        log.info("Chunk %d | Raw rows: %d", chunk_num, raw_count)

        try:
            clean = clean_chunk(raw_chunk)
        except Exception as exc:         # noqa: BLE001
            log.warning("Chunk %d cleaning raised an error, skipping: %s", chunk_num, exc)
            skipped_rows += raw_count
            continue

        written = len(clean)
        skipped_rows += raw_count - written

        if written == 0:
            log.warning("Chunk %d produced 0 clean rows — skipped DB write.", chunk_num)
            continue

        # Write to MySQL — append mode (table already exists)
        try:
            clean.to_sql(
                TABLE_NAME,
                con=engine,
                if_exists="append",
                index=False,
                method="multi",        # batch INSERT for speed
                chunksize=1_000,
            )
            total_rows_written += written
            log.info(
                "Chunk %d | Written: %d rows | Dropped: %d rows",
                chunk_num, written, raw_count - written,
            )
        except SQLAlchemyError as exc:
            log.error("Chunk %d DB write failed: %s", chunk_num, exc)
            skipped_rows += written

    elapsed = time.perf_counter() - start

    # ── Final Report
    log.info("=" * 60)
    log.info("ETL COMPLETE")
    log.info("  Total chunks processed : %d", chunk_num)
    log.info("  Total raw rows read    : %d", total_rows_raw)
    log.info("  Total rows written     : %d", total_rows_written)
    log.info("  Rows dropped/skipped   : %d", skipped_rows)
    log.info("  Elapsed time           : %.2f seconds", elapsed)
    log.info("=" * 60)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Append a cleaned investment CSV to MySQL. Use an empty target table for a fresh import.")
    parser.add_argument("--csv", default=CSV_PATH, help="Path to investments_VC.csv (or set CSV_PATH)")
    run_etl(parser.parse_args().csv)
