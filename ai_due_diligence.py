"""
ai_due_diligence.py
====================
GenAI Due Diligence Engine for VC Funding Analytics.

Architecture:
  - Reads startup records from `view_recent_top_startups`
  - Builds structured VC-analyst prompts per startup
  - Calls a LOCAL LLM (Ollama primary → HuggingFace fallback)
  - Stores 2-sentence Investment Thesis Summaries → MySQL

Local LLM priority order:
  1. Ollama  (ollama run mistral)  — fastest inference, zero-config
  2. HuggingFace Transformers pipeline (CPU-safe, falcon-rw-1b / gpt2-xl)

No external paid APIs (OpenAI / Anthropic) are used.
"""

import json
import logging
import sys
import time
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "vc_analytics_db")
VIEW_NAME   = "view_recent_top_startups"
SUMMARY_TBL = "ai_due_diligence_summaries"

# Ollama settings
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT   = 60                 # seconds

# HuggingFace fallback model (small enough to run on CPU)
HF_MODEL_NAME    = "tiiuae/falcon-rw-1b"

# Processing controls
BATCH_SIZE       = 2      # startups per DB commit
MAX_RECORDS      = 500    # cap for a single run (set to None for unlimited)
JSON_STORE_PATH  = "ai_summaries.json"   # secondary JSON store

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ai_due_diligence.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Data Model
# ──────────────────────────────────────────────

@dataclass
class StartupRecord:
    id:             int
    name:           str
    market:         str
    funding_tier:   str
    maturity_stage: str
    country_code:   str
    funding_mn_usd: float
    founded_year:   Optional[int]
    ai_prompt_context: str


@dataclass
class DueDiligenceSummary:
    startup_id:       int
    startup_name:     str
    market:           str
    funding_tier:     str
    maturity_stage:   str
    country_code:     str
    investment_thesis: str
    model_used:       str


# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────

def build_engine():
    url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, echo=False)


def fetch_startups(engine) -> pd.DataFrame:
    """Pull all records from the AI-ready view."""
    limit_clause = f"LIMIT {MAX_RECORDS}" if MAX_RECORDS else ""
    query = f"""
        SELECT
            id, name, market, funding_tier, maturity_stage,
            country_code, funding_mn_usd, founded_year, ai_prompt_context
        FROM `{VIEW_NAME}`
        {limit_clause}
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    log.info("Fetched %d startup records from view '%s'.", len(df), VIEW_NAME)
    return df


def summaries_already_done(engine) -> set:
    """Return set of startup_ids already stored to avoid re-processing."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT startup_id FROM `{SUMMARY_TBL}`"))
            return {row[0] for row in result.fetchall()}
    except Exception:  # noqa: BLE001
        return set()


def batch_insert_summaries(engine, summaries: list[DueDiligenceSummary]):
    """Bulk-insert a list of DueDiligenceSummary objects into MySQL."""
    if not summaries:
        return
    rows = [asdict(s) for s in summaries]
    df   = pd.DataFrame(rows)
    try:
        df.to_sql(SUMMARY_TBL, con=engine, if_exists="append", index=False, method="multi")
        log.info("  -> Persisted %d summaries to MySQL.", len(summaries))
    except SQLAlchemyError as exc:
        log.error("DB insert failed: %s", exc)


# ──────────────────────────────────────────────
# Prompt Engineering
# ──────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a seasoned Venture Capital Analyst at a top-tier global investment firm. "
    "Your role is to produce concise, data-driven investment thesis summaries for startups. "
    "Each summary must be exactly two sentences:\n"
    "  Sentence 1: Identify the dominant technology trend and sector this startup addresses.\n"
    "  Sentence 2: Assess sector viability and investment attractiveness based on the funding "
    "data, market maturity, and operational status.\n"
    "Be specific, professional, and avoid generic filler phrases."
)

def build_user_prompt(rec: StartupRecord) -> str:
    return (
        f"Company Profile:\n"
        f"  {rec.ai_prompt_context}\n\n"
        f"Additional Context:\n"
        f"  - Funding Tier   : {rec.funding_tier}\n"
        f"  - Maturity Stage : {rec.maturity_stage}\n"
        f"  - Total Raised   : ${rec.funding_mn_usd:.2f}M USD\n"
        f"  - Founded        : {rec.founded_year}\n\n"
        f"Task: Write a structured, 2-sentence Investment Thesis Summary for this startup.\n"
        f"Investment Thesis Summary:"
    )


# ──────────────────────────────────────────────
# LLM Backends
# ──────────────────────────────────────────────

class OllamaBackend:
    """Calls local Ollama server (must be running: `ollama serve`)."""

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.endpoint = f"{OLLAMA_BASE_URL}/api/generate"

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def generate(self, system: str, user: str) -> str:
        payload = {
            "model":  self.model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p":       0.9,
                "num_predict": 150,
            },
        }
        r = requests.post(self.endpoint, json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()

    @property
    def model_id(self) -> str:
        return f"ollama/{self.model}"


class HuggingFaceBackend:
    """
    CPU-safe HuggingFace text-generation pipeline fallback.
    Downloads model on first run and caches locally.
    """

    def __init__(self, model_name: str = HF_MODEL_NAME):
        self.model_name = model_name
        self._pipe = None

    def _load(self):
        if self._pipe is None:
            log.info("Loading HuggingFace model '%s' (first-time download may take a while)…", self.model_name)
            from transformers import pipeline, AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._pipe = pipeline(
                "text-generation",
                model=self.model_name,
                tokenizer=tokenizer,
                device=-1,            # CPU
                max_new_tokens=150,
                do_sample=True,
                temperature=0.4,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
            log.info("HuggingFace model loaded.")

    def generate(self, system: str, user: str) -> str:
        self._load()
        combined = f"{system}\n\n{user}"
        out = self._pipe(combined, return_full_text=False)
        return out[0]["generated_text"].strip()

    @property
    def model_id(self) -> str:
        return f"huggingface/{self.model_name}"


class LLMRouter:
    """Selects the best available backend at runtime."""

    def __init__(self):
        self._ollama = OllamaBackend()
        self._hf     = HuggingFaceBackend()
        self._active = None

    def _pick_backend(self):
        if self._active:
            return self._active
        if self._ollama.is_available():
            log.info("LLM Backend: Ollama (%s) [OK]", OLLAMA_MODEL)
            self._active = self._ollama
        else:
            log.warning("Ollama not detected. Falling back to HuggingFace (%s).", HF_MODEL_NAME)
            self._active = self._hf
        return self._active

    def generate(self, system: str, user: str) -> tuple[str, str]:
        """Returns (generated_text, model_id)."""
        backend = self._pick_backend()
        text_out = backend.generate(system, user)
        return text_out, backend.model_id


# ──────────────────────────────────────────────
# Post-processing utilities
# ──────────────────────────────────────────────

def sanitize_thesis(raw: str) -> str:
    """
    Trim generated text to at most 2 complete sentences and clean up artefacts.
    """
    # Remove leading/trailing whitespace & repeated newlines
    raw = " ".join(raw.split())

    # Keep only the first 2 sentences (split on ". " or "! " or "? ")
    import re
    sentences = re.split(r'(?<=[.!?])\s+', raw.strip())
    thesis = " ".join(sentences[:2]).strip()

    # Fallback: if model returned nothing meaningful
    if len(thesis) < 20:
        thesis = "Insufficient data for a conclusive investment thesis. Further diligence required."

    return thesis


# ──────────────────────────────────────────────
# Main processing loop
# ──────────────────────────────────────────────

def run_due_diligence():
    t_start = time.perf_counter()
    log.info("=" * 60)
    log.info("AI Due Diligence Engine - START")
    log.info("=" * 60)

    engine = build_engine()
    df     = fetch_startups(engine)

    if df.empty:
        log.warning("No records returned from view. Run the ETL pipeline first.")
        return

    done_ids = summaries_already_done(engine)
    df = df[~df["id"].isin(done_ids)]
    log.info("%d records to process (%d already done).", len(df), len(done_ids))

    if df.empty:
        log.info("All records already have summaries. Nothing to do.")
        return

    router   = LLMRouter()
    pending  = []
    json_out = []
    ok_count = 0
    err_count= 0

    for i, row in df.iterrows():
        rec = StartupRecord(
            id             = int(row["id"]),
            name           = str(row["name"]),
            market         = str(row["market"]),
            funding_tier   = str(row["funding_tier"]),
            maturity_stage = str(row["maturity_stage"]),
            country_code   = str(row["country_code"]),
            funding_mn_usd = float(row["funding_mn_usd"] or 0),
            founded_year   = int(row["founded_year"]) if pd.notna(row.get("founded_year")) else None,
            ai_prompt_context = str(row["ai_prompt_context"]),
        )

        log.info("[%d/%d] Generating thesis for: %s", ok_count + err_count + 1, len(df), rec.name)

        try:
            raw_thesis, model_id = router.generate(SYSTEM_PROMPT, build_user_prompt(rec))
            thesis = sanitize_thesis(raw_thesis)
        except Exception as exc:  # noqa: BLE001
            log.error("  LLM error for '%s': %s", rec.name, exc)
            thesis   = "LLM generation failed; manual review required."
            model_id = "error"
            err_count += 1

        summary = DueDiligenceSummary(
            startup_id       = rec.id,
            startup_name     = rec.name,
            market           = rec.market,
            funding_tier     = rec.funding_tier,
            maturity_stage   = rec.maturity_stage,
            country_code     = rec.country_code,
            investment_thesis= thesis,
            model_used       = model_id,
        )
        pending.append(summary)
        json_out.append(asdict(summary))
        ok_count += 1

        log.info("  -> Thesis: %s", thesis[:120] + "..." if len(thesis) > 120 else thesis)

        # Batch commit every BATCH_SIZE records
        if len(pending) >= BATCH_SIZE:
            batch_insert_summaries(engine, pending)
            pending.clear()

    # Commit any remaining
    batch_insert_summaries(engine, pending)

    # ── Write JSON store (secondary output)
    with open(JSON_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    log.info("JSON summaries written -> %s", JSON_STORE_PATH)

    elapsed = time.perf_counter() - t_start
    log.info("=" * 60)
    log.info("AI Due Diligence - COMPLETE")
    log.info("  Processed  : %d startups", ok_count)
    log.info("  Errors     : %d", err_count)
    log.info("  Elapsed    : %.2f seconds (avg %.2fs/startup)", elapsed, elapsed / max(ok_count, 1))
    log.info("=" * 60)


if __name__ == "__main__":
    run_due_diligence()
