-- ============================================================
-- vc_analytics.sql
-- Production SQL: Schema + Advanced Analytics for VC Dashboard
-- ============================================================
-- Run order:
--   1. Schema & table creation  (Section A)
--   2. Window function query     (Section B)
--   3. CTE query                 (Section C)
--   4. View creation             (Section D)
-- ============================================================

-- ──────────────────────────────────────────────────────────────
-- SECTION A: DATABASE & TABLE SCHEMA
-- ──────────────────────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS `vc_analytics_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `vc_analytics_db`;

-- Primary investments table (created by ETL pipeline; this DDL
-- is provided here for reference / standalone setup).
CREATE TABLE IF NOT EXISTS `startup_investments` (
    id                  BIGINT          AUTO_INCREMENT  PRIMARY KEY,
    name                VARCHAR(512)    NULL,
    market              VARCHAR(255)    NULL,
    funding_total_usd   DOUBLE          NULL COMMENT 'Total raised (USD)',
    status              VARCHAR(100)    NULL COMMENT 'operating | acquired | closed | ipo',
    country_code        CHAR(10)        NULL,
    founded_year        SMALLINT        NULL,
    funding_rounds      SMALLINT        NULL,
    first_funding_at    DATE            NULL,
    last_funding_at     DATE            NULL,
    inserted_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    -- Performance indexes
    INDEX idx_market    (market(100)),
    INDEX idx_country   (country_code),
    INDEX idx_year      (founded_year),
    INDEX idx_funding   (funding_total_usd),
    INDEX idx_status    (status)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Raw VC investment records loaded by etl_pipeline.py';


-- ──────────────────────────────────────────────────────────────
-- SECTION B: WINDOW FUNCTION — Cumulative Funding Velocity
-- ──────────────────────────────────────────────────────────────
-- Purpose : For every market sector, compute:
--             1. Total funding raised in that year (yearly_funding)
--             2. Running cumulative sum ordered by year             (cumulative_funding)
--             3. Year-over-year funding growth percentage           (yoy_growth_pct)
--             4. Rank of the market within each year               (market_rank_in_year)
-- ──────────────────────────────────────────────────────────────

SELECT
    market,
    founded_year,

    -- Annual aggregate for this market × year cell
    COUNT(*)                                                        AS startup_count,
    SUM(funding_total_usd)                                          AS yearly_funding_usd,
    AVG(funding_total_usd)                                          AS avg_funding_usd,

    -- Cumulative funding velocity: running sum per market over time
    SUM(SUM(funding_total_usd))
        OVER (
            PARTITION BY market
            ORDER BY founded_year
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                           AS cumulative_funding_usd,

    -- Year-over-year growth within the same market
    ROUND(
        100.0 * (
            SUM(funding_total_usd) -
            LAG(SUM(funding_total_usd), 1)
                OVER (PARTITION BY market ORDER BY founded_year)
        ) /
        NULLIF(
            LAG(SUM(funding_total_usd), 1)
                OVER (PARTITION BY market ORDER BY founded_year),
            0
        ),
        2
    )                                                               AS yoy_growth_pct,

    -- Rank of this market in the given year (most-funded = 1)
    RANK()
        OVER (
            PARTITION BY founded_year
            ORDER BY SUM(funding_total_usd) DESC
        )                                                           AS market_rank_in_year

FROM `startup_investments`
WHERE
    market              IS NOT NULL
    AND founded_year    IS NOT NULL
    AND founded_year    BETWEEN 1990 AND 2030
    AND funding_total_usd IS NOT NULL
    AND funding_total_usd  > 0

GROUP BY
    market,
    founded_year

ORDER BY
    market,
    founded_year;


-- ──────────────────────────────────────────────────────────────
-- SECTION C: CTE — Investment Concentration in Top 1% Startups
-- ──────────────────────────────────────────────────────────────
-- Purpose : Isolate the top 1% of startups by total funding,
--           then analyse investment concentration by country
--           and operational status within that elite tier.
-- ──────────────────────────────────────────────────────────────

WITH ranked_for_p99 AS (
    -- Step 1a: Rank every row by funding to compute PERCENT_RANK
    SELECT
        funding_total_usd,
        PERCENT_RANK() OVER (ORDER BY funding_total_usd) AS pct_rank
    FROM `startup_investments`
    WHERE funding_total_usd IS NOT NULL
      AND funding_total_usd > 0
),

percentile_99 AS (
    -- Step 1b: Pick the lowest value whose PERCENT_RANK >= 0.99 (≈ 99th percentile)
    SELECT MIN(funding_total_usd) AS threshold_usd
    FROM ranked_for_p99
    WHERE pct_rank >= 0.99
),

top_1pct_startups AS (
    -- Step 2: Filter startups that sit at or above the 99th percentile
    SELECT
        s.id,
        s.name,
        s.market,
        s.funding_total_usd,
        s.status,
        s.country_code,
        s.founded_year,
        s.funding_rounds,
        p.threshold_usd
    FROM `startup_investments`  s
    CROSS JOIN percentile_99    p
    WHERE s.funding_total_usd  >= p.threshold_usd
      AND s.funding_total_usd  IS NOT NULL
      AND s.country_code       IS NOT NULL
      AND s.status             IS NOT NULL
),

country_concentration AS (
    -- Step 3: Aggregate concentration metrics per country × status
    SELECT
        country_code,
        status,
        COUNT(*)                                AS startup_count,
        SUM(funding_total_usd)                  AS total_funding_usd,
        AVG(funding_total_usd)                  AS avg_funding_usd,
        MAX(funding_total_usd)                  AS max_funding_usd,
        MIN(funding_total_usd)                  AS min_funding_usd,
        COUNT(DISTINCT market)                  AS distinct_markets,
        MIN(founded_year)                       AS earliest_founded,
        MAX(founded_year)                       AS latest_founded,
        MAX(threshold_usd)                      AS global_p99_threshold
    FROM top_1pct_startups
    GROUP BY
        country_code,
        status
)

-- Step 4: Final output with share-of-total enrichment
SELECT
    cc.country_code,
    cc.status,
    cc.startup_count,
    ROUND(cc.total_funding_usd / 1e9, 3)        AS total_funding_bn_usd,
    ROUND(cc.avg_funding_usd   / 1e6, 2)        AS avg_funding_mn_usd,
    ROUND(cc.max_funding_usd   / 1e9, 3)        AS max_funding_bn_usd,
    cc.distinct_markets,
    cc.earliest_founded,
    cc.latest_founded,

    -- Share of total top-1% funding captured by this country × status
    ROUND(
        100.0 * cc.total_funding_usd /
        NULLIF(SUM(cc.total_funding_usd) OVER (), 0),
        4
    )                                           AS pct_of_top1pct_funding,

    -- Rank countries by total investment received in top tier
    RANK()
        OVER (ORDER BY cc.total_funding_usd DESC) AS country_rank

FROM country_concentration cc

ORDER BY
    total_funding_usd DESC,
    country_code,
    status;


-- ──────────────────────────────────────────────────────────────
-- SECTION D: VIEW — Recent High-Funded Startups for AI Analysis
-- ──────────────────────────────────────────────────────────────
-- Purpose : Materialise a clean, enriched view that the AI Due
--           Diligence engine reads to build LLM prompts.
--           Criteria: founded in the last 15 years AND funding
--           above the overall median.
-- ──────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW `view_recent_top_startups` AS
WITH ranked_for_median AS (
    -- Rank all rows to compute 50th percentile (median) via PERCENT_RANK
    SELECT
        funding_total_usd,
        PERCENT_RANK() OVER (ORDER BY funding_total_usd) AS pct_rank
    FROM `startup_investments`
    WHERE funding_total_usd IS NOT NULL
      AND funding_total_usd  > 0
),
median_funding AS (
    SELECT MIN(funding_total_usd) AS median_usd
    FROM ranked_for_median
    WHERE pct_rank >= 0.5
)
SELECT
    s.id,
    s.name,
    COALESCE(s.market, 'Unknown Sector')                AS market,
    s.funding_total_usd,
    ROUND(s.funding_total_usd / 1e6, 2)                AS funding_mn_usd,
    s.status,
    COALESCE(s.country_code, 'N/A')                     AS country_code,
    s.founded_year,
    s.funding_rounds,
    s.first_funding_at,
    s.last_funding_at,
    m.median_usd                                        AS global_median_usd,

    -- Funding tier classification for prompt engineering
    CASE
        WHEN s.funding_total_usd >= 1e9  THEN 'Unicorn (≥$1B)'
        WHEN s.funding_total_usd >= 1e8  THEN 'Series D+ ($100M–$1B)'
        WHEN s.funding_total_usd >= 1e7  THEN 'Series B/C ($10M–$100M)'
        WHEN s.funding_total_usd >= 1e6  THEN 'Series A ($1M–$10M)'
        ELSE                                  'Seed / Early'
    END                                                 AS funding_tier,

    -- Market maturity signal
    CASE
        WHEN s.founded_year >= YEAR(CURDATE()) - 5  THEN 'Emerging'
        WHEN s.founded_year >= YEAR(CURDATE()) - 10 THEN 'Growth'
        ELSE                                             'Established'
    END                                                 AS maturity_stage,

    -- AI prompt-ready description field
    CONCAT(
        COALESCE(s.name, 'Unknown'),
        ' is a ',
        COALESCE(s.status, 'active'),
        ' startup in the ',
        COALESCE(s.market, 'technology'),
        ' sector, founded in ',
        COALESCE(s.founded_year, 0),
        ', headquartered in ',
        COALESCE(s.country_code, 'an undisclosed location'),
        ', and has raised $',
        FORMAT(COALESCE(s.funding_total_usd, 0), 0),
        ' USD in total funding across ',
        COALESCE(s.funding_rounds, 0),
        ' rounds.'
    )                                                   AS ai_prompt_context

FROM `startup_investments`  s
CROSS JOIN median_funding    m
WHERE
    s.founded_year      IS NOT NULL
    AND s.founded_year  >= YEAR(CURDATE()) - 15
    AND s.funding_total_usd IS NOT NULL
    AND s.funding_total_usd  > m.median_usd
    AND s.name           IS NOT NULL

ORDER BY
    s.funding_total_usd DESC;


-- ──────────────────────────────────────────────────────────────
-- SECTION E: AI Summaries Table (populated by ai_due_diligence.py)
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `ai_due_diligence_summaries` (
    id                  BIGINT          AUTO_INCREMENT  PRIMARY KEY,
    startup_id          BIGINT          NOT NULL        COMMENT 'FK → startup_investments.id',
    startup_name        VARCHAR(512)    NOT NULL,
    market              VARCHAR(255),
    funding_tier        VARCHAR(50),
    maturity_stage      VARCHAR(50),
    country_code        CHAR(10),
    investment_thesis   TEXT            NOT NULL        COMMENT '2-sentence LLM-generated summary',
    model_used          VARCHAR(128)    DEFAULT 'ollama/mistral',
    generated_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_startup   (startup_id),
    INDEX idx_name      (startup_name(100)),
    INDEX idx_market    (market(100))
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='LLM-generated investment thesis summaries per startup';


-- ──────────────────────────────────────────────────────────────
-- SECTION F: Convenience Queries for Flask API Endpoints
-- ──────────────────────────────────────────────────────────────

-- /api/funding-trends  →  top markets, yearly cumulative velocity
-- (Copy of Section B materialised for the Flask route)
-- SELECT market, founded_year, cumulative_funding_usd FROM (
--     SELECT market, founded_year,
--            SUM(SUM(funding_total_usd)) OVER (PARTITION BY market ORDER BY founded_year) AS cumulative_funding_usd
--     FROM startup_investments WHERE market IS NOT NULL AND founded_year IS NOT NULL AND funding_total_usd > 0
--     GROUP BY market, founded_year
-- ) sub ORDER BY cumulative_funding_usd DESC;

-- /api/ai-summaries  →  latest LLM summaries
-- SELECT startup_name, market, funding_tier, investment_thesis, generated_at
-- FROM ai_due_diligence_summaries ORDER BY generated_at DESC LIMIT 50;
