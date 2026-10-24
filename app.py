"""
app.py
=======
Flask REST API — VC Funding Analytics & AI Due Diligence Engine

Endpoints:
  GET /                          → serves index.html
  GET /api/funding-trends        → cumulative funding velocity by market × year
  GET /api/top-markets           → top 15 markets by total funding
  GET /api/country-concentration → investment concentration by country
  GET /api/ai-summaries          → latest LLM-generated investment thesis cards
  GET /api/stats                 → high-level KPI dashboard stats
  GET /api/health                → liveness check
"""

import logging
import urllib.parse
from functools import wraps

import pandas as pd
from flask import Flask, jsonify, render_template_string, send_from_directory, abort
from flask_cors import CORS
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# App & DB
# ──────────────────────────────────────────────

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)   # allow requests from any origin (dev mode)

def get_engine():
    url = os.getenv("DATABASE_URL") or f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, echo=False)

engine = get_engine()

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def db_error_handler(f):
    """Decorator: wrap route functions to catch DB errors gracefully."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as exc:
            log.error("Database error in %s: %s", f.__name__, exc)
            return jsonify({"error": "Database unavailable. Please try again shortly."}), 500
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected error in %s: %s", f.__name__, exc)
            return jsonify({"error": "Internal server error"}), 500
    return wrapper


def query_df(sql: str, params: dict = None) -> pd.DataFrame:
    """Execute a SQL query and return a cleaned DataFrame."""
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params or {})
    # Convert NaN → None for clean JSON serialisation
    return df.astype(object).where(pd.notnull(df), None)


# ──────────────────────────────────────────────
# Routes — Static
# ──────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main dashboard HTML file."""
    import os
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(html_path):
        abort(404, "index.html not found — run the project setup.")
    with open(html_path, encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}


# ──────────────────────────────────────────────
# Routes — API
# ──────────────────────────────────────────────

@app.route("/api/health")
def health():
    """Liveness probe."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected", "database_type": engine.dialect.name,
                        "ai_configured": bool(os.getenv("GROQ_API_KEY"))})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "degraded", "error": "Database unavailable"}), 503


@app.route("/api/stats")
@db_error_handler
def api_stats():
    """
    High-level KPI metrics for the dashboard header cards.
    Returns: total startups, total funding, top market, top country.
    """
    sql = """
        SELECT
            COUNT(*)                              AS total_startups,
            ROUND(SUM(funding_total_usd)/1e9, 2) AS total_funding_bn,
            COUNT(DISTINCT market)                AS total_markets,
            COUNT(DISTINCT country_code)          AS total_countries
        FROM startup_investments
        WHERE funding_total_usd IS NOT NULL
    """
    row = query_df(sql).iloc[0].to_dict()

    # Top market
    top_market_sql = """
        SELECT market, SUM(funding_total_usd) AS total
        FROM startup_investments
        WHERE market IS NOT NULL AND funding_total_usd IS NOT NULL
        GROUP BY market ORDER BY total DESC LIMIT 1
    """
    top_market = query_df(top_market_sql)
    row["top_market"] = top_market.iloc[0]["market"] if not top_market.empty else "N/A"

    # Top country
    top_country_sql = """
        SELECT country_code, SUM(funding_total_usd) AS total
        FROM startup_investments
        WHERE country_code IS NOT NULL AND funding_total_usd IS NOT NULL
        GROUP BY country_code ORDER BY total DESC LIMIT 1
    """
    top_country = query_df(top_country_sql)
    row["top_country"] = top_country.iloc[0]["country_code"] if not top_country.empty else "N/A"

    return jsonify(row)


@app.route("/api/funding-trends")
@db_error_handler
def api_funding_trends():
    """
    Cumulative funding velocity per market × year (window function).
    Used by the Chart.js line chart.
    Query param: ?markets=Biotech,Mobile,SaaS  (optional filter)
    """
    sql = """
        SELECT
            market,
            founded_year,
            ROUND(SUM(funding_total_usd)/1e6, 2)              AS yearly_funding_mn,
            ROUND(
                SUM(SUM(funding_total_usd))
                OVER (PARTITION BY market ORDER BY founded_year
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                / 1e6, 2
            )                                                  AS cumulative_funding_mn,
            COUNT(*)                                           AS startup_count
        FROM startup_investments
        WHERE
            market           IS NOT NULL
            AND founded_year IS NOT NULL
            AND founded_year BETWEEN 1995 AND 2023
            AND funding_total_usd > 0
        GROUP BY market, founded_year
        ORDER BY market, founded_year
    """
    df = query_df(sql)

    # Restrict to top 10 markets by total lifetime funding for clean chart
    top_markets_sql = """
        SELECT market
        FROM startup_investments
        WHERE market IS NOT NULL AND funding_total_usd > 0
        GROUP BY market
        ORDER BY SUM(funding_total_usd) DESC
        LIMIT 10
    """
    top_markets = query_df(top_markets_sql)["market"].tolist()
    df = df[df["market"].isin(top_markets)]

    # Pivot: years as labels, each market as a dataset
    if df.empty:
        return jsonify({"labels": [], "datasets": []})

    years = sorted(df["founded_year"].dropna().unique().tolist())
    datasets = []
    palette = [
        "#6C63FF","#FF6584","#43E8D8","#F7B731","#FC5C65",
        "#26de81","#fd9644","#4bcffa","#a55eea","#ff5e57"
    ]
    for idx, mkt in enumerate(top_markets):
        mkt_df = df[df["market"] == mkt].set_index("founded_year")
        data   = [mkt_df.loc[y, "cumulative_funding_mn"] if y in mkt_df.index else None for y in years]
        color  = palette[idx % len(palette)]
        datasets.append({
            "label":           mkt,
            "data":            data,
            "borderColor":     color,
            "backgroundColor": color + "22",
            "tension":         0.4,
            "fill":            False,
            "pointRadius":     3,
        })

    return jsonify({"labels": years, "datasets": datasets})


@app.route("/api/top-markets")
@db_error_handler
def api_top_markets():
    """Top 15 markets by total funding — for bar chart."""
    sql = """
        SELECT
            market,
            COUNT(*)                                      AS startup_count,
            ROUND(SUM(funding_total_usd)/1e9, 3)          AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6, 2)          AS avg_funding_mn,
            COUNT(DISTINCT country_code)                  AS countries_represented
        FROM startup_investments
        WHERE market IS NOT NULL AND funding_total_usd > 0
        GROUP BY market
        ORDER BY total_funding_bn DESC
        LIMIT 15
    """
    df = query_df(sql)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/country-concentration")
@db_error_handler
def api_country_concentration():
    """
    Investment concentration in top-1% startups, grouped by country.
    Implements the CTE logic from vc_analytics.sql.
    """
    sql = """
        WITH ranked AS (
            SELECT *,
                   PERCENT_RANK() OVER (ORDER BY funding_total_usd) AS pct_rank
            FROM startup_investments
            WHERE funding_total_usd IS NOT NULL AND funding_total_usd > 0
              AND country_code IS NOT NULL
        )
        SELECT
            country_code,
            status,
            COUNT(*)                               AS startup_count,
            ROUND(SUM(funding_total_usd)/1e9, 3)   AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6, 2)   AS avg_funding_mn,
            COUNT(DISTINCT market)                 AS distinct_markets
        FROM ranked
        WHERE pct_rank >= 0.99
        GROUP BY country_code, status
        ORDER BY total_funding_bn DESC
        LIMIT 50
    """
    df = query_df(sql)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/ai-summaries")
@db_error_handler
def api_ai_summaries():
    """
    Latest LLM-generated investment thesis summaries.
    Query params:
      ?limit=20        (default 20, max 100)
      ?market=Biotech  (optional market filter)
    """
    from flask import request as req

    limit  = min(int(req.args.get("limit", 20)), 100)
    market = req.args.get("market", None)

    where  = "WHERE 1=1"
    params = {"limit": limit}
    if market:
        where += " AND market = :market"
        params["market"] = market

    sql = f"""
        SELECT
            s.startup_name,
            s.market,
            s.funding_tier,
            s.maturity_stage,
            s.country_code,
            s.investment_thesis,
            s.model_used,
            s.generated_at
        FROM ai_due_diligence_summaries s
        {where}
        ORDER BY s.generated_at DESC
        LIMIT :limit
    """
    df = query_df(sql, params)

    if df.empty:
        # Return demo data if AI engine hasn't run yet
        demo = [
            {
                "startup_name":     "Stripe",
                "market":           "FinTech",
                "funding_tier":     "Unicorn (≥$1B)",
                "maturity_stage":   "Growth",
                "country_code":     "USA",
                "investment_thesis": (
                    "Stripe operates at the intersection of financial infrastructure and developer-centric API "
                    "commerce, capitalising on the accelerating global shift toward embedded payments and SaaS "
                    "monetisation tooling. "
                    "The FinTech payments sector exhibits sustained double-digit CAGR driven by e-commerce "
                    "expansion and cross-border transaction growth, making Stripe a high-conviction, "
                    "long-horizon investment with strong network-effect moats."
                ),
                "model_used":   "demo",
                "generated_at": "2025-01-01T00:00:00",
            },
            {
                "startup_name":     "Moderna",
                "market":           "Biotechnology",
                "funding_tier":     "Unicorn (≥$1B)",
                "maturity_stage":   "Established",
                "country_code":     "USA",
                "investment_thesis": (
                    "Moderna's mRNA technology platform represents a paradigm shift in therapeutic development, "
                    "enabling rapid programmable vaccine and drug candidate creation across oncology, "
                    "infectious disease, and rare conditions. "
                    "Biotechnology remains one of the most capital-intensive yet highest-return sectors, "
                    "with Moderna's diversified pipeline and government-backed revenue channels significantly "
                    "de-risking near-term commercialisation prospects."
                ),
                "model_used":   "demo",
                "generated_at": "2025-01-01T00:00:00",
            },
        ]
        return jsonify({"source": "demo", "records": demo})

    return jsonify({
        "source":  engine.dialect.name,
        "records": df.to_dict(orient="records"),
    })


@app.route("/api/funding-by-status")
@db_error_handler
def api_funding_by_status():
    """Funding breakdown by startup status (operating, acquired, closed, ipo)."""
    sql = """
        SELECT
            COALESCE(status, 'Unknown')              AS status,
            COUNT(*)                                 AS count,
            ROUND(SUM(funding_total_usd)/1e9, 3)     AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6, 2)     AS avg_funding_mn
        FROM startup_investments
        WHERE funding_total_usd IS NOT NULL AND funding_total_usd > 0
        GROUP BY status
        ORDER BY total_funding_bn DESC
    """
    df = query_df(sql)
    return jsonify(df.to_dict(orient="records"))


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

from cloud_ai import register_cloud_ai
register_cloud_ai(app, engine)

if __name__ == "__main__":
    log.info("Starting VC Analytics Flask Server on http://localhost:5000")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False, use_reloader=False)
