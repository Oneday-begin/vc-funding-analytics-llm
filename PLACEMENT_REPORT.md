# Venture Atlas Placement Preparation Report

**Project:** Venture Atlas - VC Funding Analytics and AI Research Workspace
**Purpose:** Technical understanding, placement preparation, project demonstration, and deployment reference
**Prepared:** 25 October 2026
**Application baseline inspected:** `1678184e8d6243721c56d8d9558b647df8e7dcb3`
**Live application:** https://vc-funding-analytics.onrender.com
**Repository:** https://github.com/Oneday-begin/vc-funding-analytics-llm

This report explains the actual repository from input data to the deployed user interface. Read the quick preparation section first, study the implementation chapters next, and rehearse with the interview questions. The final chapter contains the procedure for deploying after future changes. No live password, API key, access token, or private database URL is included.

The project is an interactive portfolio application over a historical company dataset. Its current online implementation uses Flask, parameterized SQL through SQLAlchemy, SQLite, native browser charts, and hosted Groq inference. Separate MySQL ETL, SQL analysis, Ollama, and Hugging Face scripts remain available in the repository. Those are different execution paths; do not describe every technology as running in the online service.

## Contents

1. How to prepare efficiently
2. Abstract and problem definition
3. Objectives and requirements
4. Verified dataset and interpretation
5. Technology stack and configuration
6. Architecture and end to end flows
7. Repository and module responsibilities
8. Application startup and request lifecycle
9. Database design and relationships
10. Data ingestion and cleaning
11. SQL analytics and worked examples
12. Complete API reference
13. Frontend implementation and user experience
14. Hosted AI implementation
15. Retained MySQL and local AI workflow
16. Computer science concepts used
17. Security audit and secret handling
18. Testing and continuous integration
19. Performance and scalability
20. Error handling and troubleshooting
21. Limitations and honest project boundaries
22. Design decisions and future improvements
23. Demonstration and placement presentation
24. Interview questions and model answers
25. Glossary and last minute revision
26. References and evidence
27. Deployment after changes

## 1 How to prepare efficiently

### 1.1 A practical study sequence

| Time available | Study priority | Outcome |
| --- | --- | --- |
| 15 minutes | Sections 1, 4, 6, 21 and 25 | Explain the project without making false claims |
| 45 minutes | Add sections 5, 8, 9, 11 and 14 | Trace a request and defend the main technical choices |
| Two hours | Add sections 10, 12, 13, 17 and 18 | Explain individual modules, edge cases, security and tests |
| Before an interview | Rehearse section 23 and questions in section 24 | Give a coherent demonstration and handle follow-up questions |
| Before changing or publishing code | Follow section 27 | Test, scan and deploy safely |

### 1.2 The 60 second explanation

> Venture Atlas is a full-stack research workspace for a historical venture funding dataset. It lets a user filter market and country analytics, search company records, inspect profiles, export results, and generate an AI research note from a selected profile. The deployed application uses Flask and SQLAlchemy with SQLite, while the browser renders the interface and SVG charts. Groq runs the language model remotely, so the small web server does not need to host a large model. I separate disclosed funding from valuation, and founding cohorts from annual funding flows. The project includes automated tests, server-side key handling, parameterized queries, and documented limitations.

Use first-person statements about implementation ownership only where they accurately describe your own contribution. Be prepared to open the relevant file and explain the code rather than memorizing the paragraph alone.

### 1.3 Eight facts to remember

1. The seed contains **49,438 records**, not 49,438 verified current startups.
2. **40,907 records** have positive disclosed funding; missing amounts are not zero.
3. The snapshot contains **753 market labels** and **115 country codes** across all records.
4. Founding years range from **1902 to 2014**; this does not establish collection dates.
5. The live web service uses **SQLite and hosted Groq**, not a MySQL server and local GPU model.
6. Current cohort accumulation is performed in Python after SQL grouping; the retained SQL script also demonstrates window-function accumulation.
7. AI notes are prompted from one database profile. There is no model training, vector database, live web research, or retrieval augmented generation pipeline.
8. Free hosting can reset generated server notes; browser-saved notes are local to that browser.

### 1.4 Claims to avoid

Do not claim real-time investment data, audited financial accuracy, investment recommendations, a self-trained model, guaranteed factual AI output, production-scale load testing, user authentication, cross-device saved notes, a distributed rate limiter, or fully idempotent CSV ingestion. These are not implemented capabilities.

## 2 Abstract and problem definition

### 2.1 Abstract

Venture Atlas combines data preparation, relational analytics, browser interaction, and controlled language-model inference. A cleaned investment snapshot is packaged as compressed JSON and restored into SQLite for the hosted application. Bound-parameter queries produce coverage metrics, market rankings, founding-cohort series, status distributions, country concentration, and a searchable company directory. A selected record can be submitted to a hosted language model for a short research draft. The user can copy the draft or retain it in browser storage.

The main engineering contribution is connecting these components into an inspectable, deployable workflow while making the meaning and limitations of the data explicit. The application includes input validation, finite JSON values, protected CSV exports, model error handling, request limits, local secret checks, and regression tests.

### 2.2 The problem

A raw investment CSV is difficult to explore interactively. A reader may want to know which market received more disclosed funding, which country appears among very highly funded records, or which companies match a specific sector and founding period. Without a consistent interface, these questions require repeated spreadsheet operations or ad hoc SQL. Free-form AI analysis can introduce unsupported claims if the relevant company context and boundaries are not specified.

The project addresses exploration and first-pass interpretation. It does not solve current company verification, investment selection, or prediction of financial returns.

### 2.3 Intended users and use cases

- A student demonstrating data engineering, SQL, backend, frontend and AI integration skills.
- An analyst exploring historical sector patterns and individual records.
- An interviewer inspecting implementation choices and asking technical questions.
- A visitor using the application from a phone without starting the developer's laptop.

## 3 Objectives and requirements

### 3.1 Functional requirements

| Requirement | Implemented behavior |
| --- | --- |
| Introduce the project | Landing page with a data-derived sector preview and dataset coverage |
| Explore a population | Shared market, country, status and founding-year filters |
| Read the overview | Record counts, disclosed funding, market counts and country counts |
| Compare sectors | Top-market ranking and cumulative or individual founding cohorts |
| Inspect concentration | Country totals among top-percentile funded records |
| Find companies | Literal substring search, sorting, pagination and individual profiles |
| Take data elsewhere | CSV export of the complete matching selection, not only the displayed page |
| Generate a research draft | Server-side Groq request using the selected historical profile |
| Retain a draft | Copy to clipboard or save in browser localStorage |
| Understand limitations | Methodology page and contextual definitions |
| Diagnose operation | Database health endpoint and useful error states |
| Prevent accidental disclosure | Git exclusions, redacted scans, a local commit hook and CI checks |

### 3.2 Nonfunctional objectives

The interface should work on desktop and phone screens; unsafe input should not become executable SQL or HTML; the web environment should avoid heavy local-model dependencies; external provider failure should not break the directory; setup and deployment should be reproducible; and important semantics should have automated regression tests.

These are design objectives supported by implementation and checks. There is no measured uptime service-level agreement, external penetration test, accessibility certification, or formal performance benchmark.

## 4 Verified dataset and interpretation

### 4.1 Facts measured from the bundled seed

| Measure | Verified value |
| --- | --- |
| Cleaned records | 49,438 |
| Records with disclosed positive funding | 40,907 |
| Records without a funding amount | 8,531 |
| Records with a founding year | 38,482 |
| Records without a founding year | 10,956 |
| Distinct non-null market labels across all records | 753 |
| Distinct non-null country codes across all records | 115 |
| Sum of disclosed funding | USD 650,933,703,144 |
| Dashboard-rounded funding | USD 650.93 billion |
| Earliest and latest known founding years | 1902 and 2014 |
| Compressed seed size | 690,512 bytes |
| Seed SHA256 | `bd6d228e072a6ed00c685d82fad5cd97ac67d268a9007c53d109829ec52750d7` |

These values were computed from the committed compressed seed rather than inferred from screenshots. A SHA256 value identifies the artifact's bytes; it is not a password or a certificate that the underlying data is correct.

### 4.2 Recorded statuses

| Status in the seed | Number of records |
| --- | --- |
| operating | 41,829 |
| acquired | 3,692 |
| closed | 2,603 |
| missing | 1,314 |

These are record counts, not the percentages shown by the status funding bar. The funding bar measures each status's share of disclosed funding, which is a different denominator.

### 4.3 Leading funded markets

| Market | Funded records | Disclosed funding in billions rounded to three decimals |
| --- | --- | --- |
| Biotechnology | 3,521 | 73.373 |
| Mobile | 1,710 | 49.470 |
| Software | 4,050 | 42.223 |
| Clean Technology | 1,067 | 37.620 |
| Health Care | 1,114 | 29.466 |

These rankings exclude records without positive funding and records without a market. They should not be interpreted as current sector rankings.

### 4.4 Why some older numbers differ

An earlier dashboard counted market and country labels only among funded records. That yielded 736 markets and 110 countries. The current coverage metrics count labels among all matching records, including records whose funding is undisclosed. Neither denominator should be silently substituted for the other. In an interview, explain which population a number describes.

### 4.5 Important semantic boundaries

- Total raised is cumulative disclosed funding, not revenue, profit, valuation or market capitalization.
- A founding-year cohort groups companies by when they were founded, not by when money was raised.
- A recorded status is historical, not a live verification of the business.
- Some entries describe established businesses, so “company records” is more accurate than calling every entry a startup.
- Market labels are categories from the source, not a rigorously reconciled industry taxonomy.
- The repository does not establish the original CSV's collection date, complete provenance or source licence. Do not invent an attribution or collection year.

## 5 Technology stack and configuration

### 5.1 The deployed web application

| Layer | Technology | Responsibility and reason |
| --- | --- | --- |
| Language | Python 3.12 | Backend control flow and integration; Render configuration pins 3.12.8 |
| Web framework | Flask 3.x | Routes, request parsing, Jinja rendering, responses and error handlers |
| Templates | Jinja | Shared page structure and server-rendered HTML |
| Database integration | SQLAlchemy 2.x | Engine, connection pooling, SQL text and bound parameters |
| Hosted database | SQLite | Small file-based relational store restored from the seed |
| Optional DB driver | PyMySQL | Retained compatibility with the MySQL configuration |
| HTTP client | requests 2.x | Server-to-server Groq inference request |
| Environment loading | python-dotenv 1.x | Local private configuration from an ignored environment file |
| Production server | Gunicorn 23.x | WSGI server with one worker and four threads |
| Frontend | HTML, CSS, vanilla JavaScript | Pages, responsive layout, filters, fetch requests and interaction |
| Charts | Native SVG | Paths, grid lines and bars derived from API output |
| AI service | Groq hosted inference | Runs the language model outside the small web instance |
| Model identifier | openai/gpt-oss-20b | Configurable through GROQ_MODEL; no OpenAI API key is used |
| Hosting | Render Free web service | Public HTTPS URL and linked-repository deployment |
| CI | GitHub Actions | Tests, JavaScript parsing and secret checks |

The version ranges in `requirements-web.txt` are not a lockfile. A future install can resolve newer compatible releases. Model identifiers and provider availability can also change; check the provider console when a request fails.

### 5.2 The separate local data and AI environment

`requirements.txt` additionally includes pandas, NumPy, transformers, torch, accelerate, tqdm and colorlog. pandas and NumPy support CSV cleaning and batch preparation. transformers, torch and accelerate support local inference. Ollama can serve a local Mistral model over HTTP. This heavier environment is not installed by the Render web build.

Some packages in the older requirements list, such as flask-cors, are retained dependencies but are not used by the current web application. Installed, imported and actively used are three different claims.

### 5.3 Configuration precedence

`create_app(config)` loads the ignored local environment file without intentionally overwriting already defined environment variables. The database URL supplied in the app config has priority, followed by DATABASE_URL from the process environment. If neither is present, a MySQL SQLAlchemy URL is constructed from DB_USER, DB_PASSWORD, DB_HOST, DB_PORT and DB_NAME.

For the hosted app, DATABASE_URL is `sqlite:///cloud.db`. GROQ_API_KEY is a private Render environment value. GROQ_MODEL is a non-secret model name. PORT is supplied by the hosting environment. Database user names, database names and localhost addresses are configuration, but real passwords and credential-bearing URLs must remain private.

## 6 Architecture and end to end flows

### 6.1 Current hosted architecture

```text
Browser on desktop or phone
  | GET pages and static files
  | GET JSON analytics / directory
  | POST selected company ID
  v
Render HTTPS endpoint
  v
Gunicorn WSGI server - 1 process, 4 threads
  v
Flask application factory
  |-- Jinja templates + CSS + JavaScript
  |-- analytics.py -> SQLAlchemy -> SQLite
  |-- cloud_ai.py  -> private key -> Groq HTTPS API
  |                                 |
  |                                 v
  |                         Hosted language model
  |                                 |
  +<---------- generated note -------+
  |
  +-> ai_due_diligence_summaries cache

Browser: optional localStorage note copy; no cross-device account
```

### 6.2 Data preparation path

```text
Source investments CSV
  -> pandas chunk cleaning
  -> six canonical investment fields
  -> JSON row arrays -> gzip compressed seed in Git
  -> prepare_cloud_db.py at startup
  -> SQLite records and indexes
  -> real SQL queries for the user's selected population
```

The hosted dashboard is not reading a fixed set of pre-rendered chart images. The dataset is a saved historical snapshot, but the backend queries it dynamically for filters and searches.

### 6.3 Separate legacy execution path

```text
CSV -> etl_pipeline.py -> MySQL investment table
                           |
                      vc_analytics.sql
                           |
                 view_recent_top_startups
                           |
                 ai_due_diligence.py
                           |
                Ollama or Hugging Face model
                           |
                 MySQL summaries + local JSON
```

### 6.4 Three different types of persistence

1. Git stores application source and the cleaned seed. A fresh deployment retrieves them again.
2. The hosted SQLite file stores working data and generated notes, but the free service filesystem is ephemeral.
3. localStorage stores a copy of a selected note in one browser. It persists independently of the web server but can be removed by clearing browser data.

This distinction explains why base data returns after a server restart, new server notes may disappear, and notes saved on a laptop do not automatically appear on a phone.

## 7 Repository and module responsibilities

| File or directory | Main responsibility |
| --- | --- |
| app.py | Constructs the application and exposes app:app for WSGI |
| webapp.py | App factory, config, database engine, page routes, health, HTTP errors and headers |
| analytics.py | Validation, shared filters, analytics, search, profiles, CSV and genuine summary reads |
| cloud_ai.py | Selected-profile inference, cache lookup, lock, attempt budget and provider errors |
| prepare_cloud_db.py | SQLite schema, seed restoration and indexes |
| export_cloud_seed.py | Reuses ETL cleaning and produces the compressed six-field seed |
| etl_pipeline.py | Chunked CSV cleaning and append-mode MySQL ingestion |
| ai_due_diligence.py | Retained local batch inference classes and orchestration |
| vc_analytics.sql | MySQL schema, SQL analytical examples, view and summary table |
| templates/base.html | Shared page frame, navigation, assets and footer |
| templates/landing.html | Project introduction and data-derived market preview |
| templates/dashboard.html | Analysis, directory, company dialog and research desk |
| templates/methodology.html | Dataset definitions, limitations and architecture explanation |
| templates/error.html | User-facing missing-page and HTTP error presentation |
| static/app.js | API requests, charts, revision guards, filters, search and local notes |
| static/style.css | Shared visual system, responsive rules and reduced motion |
| static/mark.svg | Brand mark and favicon |
| tests/test_app.py | Nineteen application regression tests using temporary databases |
| tests/test_secret_guard.py | Six synthetic secret-guard tests |
| scripts/check_secrets.py | Redacted current, staged and reachable-history scans |
| .githooks/pre-commit | Runs the staged-content check before a local commit |
| .github/workflows/checks.yml | Fresh-environment CI checks |
| render.yaml | Render infrastructure and runtime commands |
| .env.example | Safe configuration names and placeholders only |
| README.md and DEPLOYMENT.md | Setup and deployment guidance |

`engine` is also exposed from app.py for compatibility and inspection. Routes are registered as functions, not through a large class hierarchy or Flask Blueprint package. The project uses SQLAlchemy Core-style SQL execution; it does not define ORM entity classes for these tables.

## 8 Application startup and request lifecycle

### 8.1 Startup in the hosted service

1. Render checks out the linked branch and installs `requirements-web.txt`.
2. The start command runs `python prepare_cloud_db.py`.
3. Preparation creates missing tables and indexes and imports the seed if the investment table is empty.
4. Gunicorn imports the module named app and accesses its app object through `app:app`.
5. app.py calls `create_app()` in webapp.py.
6. The factory configures the database engine. For a file-based SQLite URL, it also calls preparation, which sees the populated table and does not append another copy.
7. The factory registers page routes, analytics routes, AI routes, error handlers and response headers.
8. Render checks `/api/health` before serving the new instance as the successful deployment.

The factory makes isolated tests possible: tests supply their own database URL and disable seed preparation. A production server imports the application; `python app.py` instead starts Flask's development server for local work.

### 8.2 A normal request

For `/api/companies?country=USA&q=Uber&page=1`, Flask matches a route, reads query parameters, validates bounded numeric inputs, builds SQL from fixed clauses and bound values, obtains a connection from the engine, executes the query, converts returned rows to dictionaries, and serializes a JSON response. The browser parses that response and updates text and rows.

An Engine is a connection-management object; constructing it is not equivalent to connecting successfully to the database. `with engine.connect()` manages a connection lifetime. `with engine.begin()` additionally provides a transaction that commits on successful completion and rolls back on failure.

### 8.3 Response conventions

Pages use HTML, APIs use JSON, and exports use CSV with an attachment filename. JSON error handlers cover HTTP exceptions on API routes. SQLAlchemy failures return a generic service-unavailable message while logging the exception type rather than exposing connection details. Responses include nosniff, a strict referrer policy, and SAMEORIGIN frame restrictions. API responses are marked no-store.

Health checks confirm that a query can reach the investment table. `ai_configured` indicates that a non-empty key exists, not that the key is valid, the provider is reachable, or a model request has succeeded.

## 9 Database design and relationships

### 9.1 Hosted investment table

| Column | SQLite type | Meaning |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY | Identifier assigned during seed insertion |
| name | TEXT | Source company name; may be absent |
| market | TEXT | Source market label |
| funding_total_usd | REAL | Disclosed total funding in USD or NULL |
| status | TEXT | Historical operating/acquired/closed label or NULL |
| country_code | TEXT | Source country code or NULL |
| founded_year | INTEGER | Known founding year or NULL |

The seed stores six source fields, not IDs. IDs are assigned when the table is populated. Regenerating or reordering the seed can change identities. A durable future cache should use a stable source identifier or an import version rather than assuming that a row number is permanent.

### 9.2 Hosted summary table

`ai_due_diligence_summaries` contains startup_id, startup_name, market, funding_tier, maturity_stage, country_code, investment_thesis, model_used and generated_at. startup_id is the SQLite primary key, giving at most one cached note per company in that table. The remaining profile fields are copied into the note record for display.

The association is logically company-to-summary, but SQLite preparation does not declare or enforce a foreign-key constraint. That is different from saying that a database-enforced FK exists. The legacy MySQL table has a separate auto-increment ID and a non-unique index on startup_id, so its duplicate behavior differs.

### 9.3 Indexes

Indexes exist on market, country_code, founded_year and funding_total_usd. They can support selection, grouping or order access depending on the database query plan. They also consume space and add insertion work. A compound index for common combinations might help larger workloads, but it should be chosen after inspecting actual plans with EXPLAIN rather than added by guesswork.

`LOWER(name) LIKE '%query%'` is a literal substring search. A normal B-tree index is usually not an effective solution to a leading wildcard search. Full-text or trigram-style search would be a more deliberate improvement for larger datasets.

### 9.4 Numeric precision and normalization

Funding uses REAL in SQLite and DOUBLE in the legacy schema. These are floating-point types. They are practical for this historical analytic demo, but a financial accounting system should use carefully defined decimal or integer minor-unit storage. Dashboard values are rounded for display; the directory retains the stored underlying amount and formats it compactly.

The investment table repeats market and country strings rather than normalizing them into lookup tables. This keeps ingestion and the small demo simple. A more governed warehouse could introduce dimensions for companies, locations, industry categories, imports and funding rounds. The current dataset does not contain all the identifiers needed for such a redesign.

## 10 Data ingestion and cleaning

### 10.1 Extract

The original MySQL importer reads the source CSV in chunks of 5,000 rows, with `unicode_escape` encoding and pandas. Chunking bounds the size of an intermediate DataFrame, although the compressed-seed exporter ultimately accumulates its output rows in memory. The source path is configurable with `--csv` or CSV_PATH rather than tied to one developer's directory.

### 10.2 Transform

1. Headers are stripped, lowercased and converted from spaces to underscores.
2. Only supported columns are selected through COLUMN_MAP.
3. Text fields are converted to strings, trimmed, mapped from known empty markers to missing values, and length-limited where applicable.
4. Funding strings have commas, dollar signs and plus signs removed; known empty markers become NaN; numeric conversion uses coercion for invalid text.
5. The first four-digit founding-year sequence is extracted and checked against 1900-2030, then stored as a nullable integer.
6. Funding-round counts are numerically coerced; date fields are parsed with invalid values coerced to missing dates.
7. Missing mandatory columns are created with missing values.
8. A row is dropped only if both name and funding are missing. The implementation does not require every field to be populated.

For example, `"$1,250,000"` becomes a numeric funding amount, `"-"` becomes missing funding, and a missing market does not require deleting an otherwise useful company record. The function called normalize_text strips and limits text; despite an older docstring, it does not actually title-case names.

### 10.3 Load into MySQL

The importer prepares the target table and uses DataFrame.to_sql in append mode, with multi-row writes batched at 1,000 records. Successfully written rows are counted after the write. Cleaning and database failures are logged and skipped. The importer is not an upsert pipeline: rerunning a file against a populated table can duplicate records.

The helper named ensure_database prepares the table using the configured connection; it should not be assumed to create a missing MySQL database. The SQL setup script supplies the CREATE DATABASE operation. There is no complete schema migration framework or exactly-once ingestion ledger.

### 10.4 Export and restore for hosting

The seed exporter reuses clean_chunk, selects name, market, funding_total_usd, status, country_code and founded_year in that order, serializes rows to JSON, and compresses them with gzip. JSON serialization converts missing numeric values to null. The compressed artifact is small enough to ship with this demo repository.

Preparation creates SQLite tables if needed, imports the seed only when the investment table is empty, creates indexes and commits the transaction. Explicit connection closing avoids keeping a database file locked after preparation. This restoration is repeatable for an unchanged populated database, but it is not a migration system: replacing the seed will not refresh an already-populated local database automatically.

### 10.5 Data engineering limitations worth knowing

There is no deduplication, categorical reconciliation, source-version table or negative-funding rejection rule. The current seed contains positive or missing funding, but the cleaner itself is not a complete domain validator. Large imports may partially succeed because failed chunks are skipped. A hardened pipeline would validate the full import, record its identity, and define restart and rollback behavior.

## 11 SQL analytics and worked examples

### 11.1 Shared selection logic

The filters helper builds fixed SQL clauses for market, country, status and a founding-year interval. Parameter values are passed separately. If a founding-year filter is set, records without a founding year do not meet that interval. Invalid bounds or an inverted interval produce a 400 error.

For a selected country, conceptual SQL is:

```sql
SELECT COUNT(*)
FROM startup_investments
WHERE country_code = :country;
```

The value of :country is bound by the database layer. It is not pasted into executable SQL. SQL strings still use f-strings to combine developer-controlled clauses; safe parameter binding depends on keeping user values out of those SQL fragments.

### 11.2 Overall statistics

COUNT(*) counts every matching record. A conditional SUM counts records with positive disclosed funding. SUM ignores NULL amounts; COALESCE makes the aggregate funding total zero when no rows contribute. COUNT(DISTINCT market) and COUNT(DISTINCT country_code) ignore NULL labels. Separate grouped queries identify the leading funded market and country.

For a tiny example containing three records with funding of 10 million, NULL and 30 million: company records is 3; funded records is 2; disclosed funding is 40 million; the funded-record average is 20 million. Treating missing as zero would incorrectly change that average to 13.33 million.

### 11.3 Market ranking

The query groups positive funded records with a known market, computes company count, total funding, average funding and countries represented, and sorts by raw total funding descending. A market-name tie breaker produces consistent results when totals tie. The API defaults to 15 markets and permits limits from 1 to 100.

The allocation bar in the UI is a market's share of funding within the displayed top 15, not its share of the entire filtered dataset. The footer and heading preserve that denominator.

### 11.4 Founding cohorts

The current endpoint first groups lifetime funding by market and founded_year. It chooses up to five leading funded markets among dated records, constructs the full year interval, and accumulates per-year values in Python. Missing cohort years contribute zero, so the running total carries forward. The browser's “By cohort” view subtracts adjacent cumulative values.

Example for one market:

| Founding year | Funding attached to that cohort in millions | Cumulative total in millions |
| --- | --- | --- |
| 2000 | 200 | 200 |
| 2001 | 0 | 200 |
| 2002 | 200 | 400 |
| 2003 | 0 | 400 |
| 2004 | 0 | 400 |
| 2005 | 1,000 | 1,400 |

This does not mean that 1,000 million was raised during 2005. It means the companies founded in 2005 have that amount of disclosed lifetime funding in the snapshot. The API accepts an optional list of at most five market names.

### 11.5 Window functions in the retained SQL script

The legacy SQL illustrates a database-side running sum:

```sql
SUM(SUM(funding_total_usd)) OVER (
  PARTITION BY market
  ORDER BY founded_year
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

The inner SUM aggregates rows in a market/year group. The outer window SUM accumulates those grouped results within each market. PARTITION BY restarts the calculation per market; ORDER BY defines the sequence; the explicit ROWS frame includes every preceding grouped row through the current one.

The script also demonstrates LAG for a preceding grouped value and RANK for relative position. These examples are present in vc_analytics.sql; they are not all active UI metrics. Avoid saying that a SQL window computes the current hosted cohort series when the deployed route uses Python accumulation.

### 11.6 Percentile concentration

The active CTE includes all filtered records with positive funding, including records without a country. PERCENT_RANK sorts ascending by funding and computes the relative rank. For more than one row, the formula is `(rank - 1) / (row_count - 1)`. Tied values share their initial rank, so the result is not identical to selecting a fixed number of rows or using NTILE(100).

The outer query keeps percentile ranks of at least 0.99, groups them by country, labels missing countries Unknown, and returns the leading country totals. Filtering before ranking changes the comparison population. Selecting one country therefore computes concentration within that country-filtered population.

For one record PERCENT_RANK is zero, so the top-percentile query returns no record. Ties can also prevent a value from reaching 0.99. The UI explains empty threshold results rather than fabricating a top group. “Top 1 percent” is a convenient label for this threshold, not a promise of exactly one percent of rows.

### 11.7 Other SQL concepts

- WHERE restricts rows before aggregation; GROUP BY forms aggregate groups.
- ORDER BY chooses a deterministic presentation order.
- LIMIT and OFFSET implement page retrieval, while a separate count query supplies total pages.
- NULL represents missing information, not an empty string or numeric zero.
- A CTE names an intermediate query result for readability and reuse within one statement; it is not automatically a permanently stored table.
- COALESCE chooses the first non-null value, making Unknown labels and empty numeric totals explicit.
- The legacy view is a saved query, not a materialized copy of all rows.

## 12 Complete API reference

### 12.1 Page routes

| Method and path | Result |
| --- | --- |
| GET / | Landing page |
| GET /dashboard | Research workspace |
| GET /methodology | Definitions, caveats and architecture notes |

### 12.2 Data routes

| Method and path | Main contract |
| --- | --- |
| GET /api/metadata | Global coverage, market/country/status options, source description |
| GET /api/stats | Matching record count, funded count, funding total, market/country counts and leaders |
| GET /api/top-markets | Array of market-level funded aggregates |
| GET /api/funding-trends | Year labels, up to five cumulative market datasets and a definition |
| GET /api/funding-by-status | Funding, funded-record count and average per recorded status |
| GET /api/country-concentration | Up to ten country aggregates from the percentile selection |
| GET /api/companies | records, total, page, per_page and pages |
| GET /api/companies/ID | One canonical historical profile or 404 |
| GET /api/companies/export.csv | All matching records as a streamed CSV attachment |
| GET /api/startups | Up to fifty funded named company choices, after applying the supplied search |
| GET /api/ai-summaries | Genuine stored notes; no illustrative fallback records |
| POST /api/generate-thesis | Generate or retrieve a note for a positive integer startup_id |
| GET /api/health | Database availability, database type and whether an AI key is configured |

### 12.3 Parameters and bounds

Shared analytics and directory parameters are market, country, status, year_from and year_to. Text filter values are trimmed and limited to 255 characters. Years must be integers between 1900 and 2030 with start no later than end. Company search q is a literal substring of name and is limited to 100 characters.

The directory defaults to page 1 and 12 records per page; per_page must be 1-100; page must be 1-100000. Sort is restricted to funding_desc, name_asc or year_desc. Each order includes id as a tie breaker. Summary reads default to a limit of 20, with a valid range of 1-100. Metadata and health do not accept the shared population filters. Research search is independent of dashboard filter state unless an API caller explicitly supplies filters to the options endpoint.

### 12.4 Safe request examples

```text
GET /api/companies?country=USA&q=Uber&page=1&per_page=12
GET /api/stats?market=Biotechnology&year_from=2000
GET /api/funding-trends?markets=Mobile,Software
POST /api/generate-thesis
Content-Type: application/json
Body: {"startup_id": 123}
```

The ID is illustrative. Use an actual selected company ID rather than assuming that 123 always identifies a specific company. No API key belongs in the browser request body or query string.

### 12.5 Response and error meanings

| Status | Meaning in this project |
| --- | --- |
| 200 | Successful page, data response, generated note or cached note |
| 400 | Invalid query bounds, sort, search length or generation body |
| 404 | Missing company or route |
| 413 | Request exceeds the 4,096 byte configured body limit |
| 429 | AI request already in progress, local minute budget exhausted, or provider quota busy |
| 502 | Upstream model failure or invalid provider configuration/response |
| 503 | Database unavailable, or live inference lacks required configuration |

A successful empty selection is a 200 with zero totals and empty lists. An empty array is not a server error. HTTP 502 can represent an upstream 401 key rejection; the user's browser is not being asked to log into the AI provider.

### 12.6 Search and export details

The search code escapes the chosen LIKE escape character, then percent and underscore, so literal names containing SQL wildcard characters behave predictably. It adds percent signs around the resulting bound value to implement substring matching. It does not treat an apostrophe as executable SQL.

CSV export shares the filters and q, but exports every matching record in funding order rather than only the current page or selected table sort. A generator streams the header and rows; StringIO is reused per row. Cells beginning with formula-trigger characters after whitespace stripping receive an apostrophe prefix. This protects spreadsheet opening behavior while preserving the database value itself.

## 13 Frontend implementation and user experience

### 13.1 Page organization

The landing page explains the project and loads a real market preview from the API. The workspace contains an overview, shared population filters, cohort chart, percentile country bars, sector ranking, funding-by-status bar, searchable company directory, profile dialog and research desk. The methodology page explains what each analysis can and cannot support.

The design uses restrained paper and forest colors, serif headings, a compact analytical hierarchy and responsive spacing. It avoids fabricated customer testimonials or performance claims. Tables can scroll horizontally on small screens; long values and phone input sizing are handled by responsive rules.

### 13.2 API requests and asynchronous state

getJSON creates an AbortController and a 55 second timeout, requests JSON, distinguishes non-JSON startup responses from valid errors, and provides useful network and timeout messages. Promise.allSettled loads independent analysis panels so one failed response does not reject every panel's result. A failure replaces the affected content with an error or empty-state explanation.

Dashboard, company, option-search and selected-profile requests have revision counters. A response is applied only if it still belongs to the newest relevant request. This prevents an old, slower response from replacing a newer search result. It does not mean that all obsolete network calls are actively canceled; most are simply ignored on arrival.

Search input uses a 300 millisecond debounce. That means a request is delayed until typing pauses; it is not the same as limiting the backend to a fixed number of requests per second. It improves interaction but does not replace server-side protection.

### 13.3 Filter and URL behavior

Applying filters updates the active filter object, resets company pagination, updates the URL query string, and reloads analysis and directory results. Query parameters are restored on initial page load, allowing a selected view to be bookmarked or shared. replaceState updates the current URL entry; the implementation is not a complete client-side router with a separate back-navigation state machine.

The research desk intentionally searches independently, so a user can compare an overview with a company outside the current population. The UI states this distinction. Selecting “Research this company” from a profile passes that actual record into the research options rather than relying on a name-only match.

### 13.4 SVG charts

The cohort chart maps years to x coordinates and funding to y coordinates within a viewBox. It computes an upper scale boundary, draws grid lines and tick labels, then draws one path per market. The legend uses matching colors. The cumulative and per-cohort views use the same source series, with adjacent subtraction for cohort amounts. A resize listener redraws the chart to keep phone axes readable.

Country and status bars are simple DOM/CSS visualizations derived from API values. The market allocation bar divides by the sum of the displayed top 15. No Chart.js dependency remains in the current interface.

### 13.5 Rendering and accessibility

Dataset names and model text are inserted through textContent and created DOM nodes rather than being pasted into innerHTML. Jinja escapes normal template content. The site includes a skip link, labelled controls, native dialogs, status/alert regions, table headings, focus styles and reduced-motion support. These are accessibility measures, not a claim of independently audited compliance.

### 13.6 Browser notes

The storage key is `venture-atlas-notes:v1`. Reads parse JSON defensively, accept an array with required text fields, and keep at most 20 notes. Saving replaces an existing note for the same company and places the current note first. The saved-note dialog can remove a local note. Copy uses the Clipboard API and reports a fallback message if clipboard access fails.

localStorage is synchronous, origin-specific, device/browser-specific and readable by scripts on that origin. It stores research notes, not the Groq key. It is not a suitable place for API secrets. A production private research product would need authenticated server-side storage and an explicit data policy.

## 14 Hosted AI implementation

### 14.1 Exact generation sequence

1. Parse the JSON body and require a positive integer startup_id. A boolean is rejected even though bool is a subclass of int in Python.
2. Try to acquire a process-local lock without waiting. If another generation is in progress, return 429.
3. Load the selected record from the database; return 404 if missing.
4. Look for an existing summary by startup_id. If found, return it with cached=true.
5. Only if no cache exists, check that GROQ_API_KEY is non-empty.
6. Remove attempt timestamps older than 60 seconds from a deque.
7. If five attempts remain, return 429 and a Retry-After value.
8. Record the new attempt and construct the model request.
9. Send the profile and system instruction to Groq using HTTPS and a private bearer header.
10. Check status, parse the completion, reject empty, non-string or oversized content, and construct a note record.
11. Insert the note in a database transaction and return cached=false.
12. Release the lock in finally, including on a failed request or database operation.

### 14.2 Model request settings

The default model is openai/gpt-oss-20b. Requests use temperature 0.4, max_completion_tokens 1024 and low reasoning effort for matching GPT-OSS model names. The connection timeout is five seconds and the read timeout is 45 seconds. A requests read timeout is not a strict total-wall-clock deadline for every possible network phase.

The system instruction asks for two concise sentences describing a sector opportunity, a strength and a risk using only the supplied historical profile. It forbids inventing current performance or interpreting funding as valuation. The user message contains JSON for the database row. The key is not included in the model context; it authenticates the HTTPS call through a header.

### 14.3 Cache and concurrency

The cache is per company ID. It is not versioned by prompt, model, dataset or profile update. Changing a model setting does not automatically regenerate an existing cached note. Cached requests avoid an external provider call and are checked before the missing-key branch. They still must acquire the same lock, so a cached request can receive a busy response while another generation holds the lock.

The lock and deque exist in the web process. One Gunicorn worker makes them service-wide for this deployment, but adding workers or replicas would create independent limiters and locks. A distributed deployment would need shared limits and a concurrency-safe cache strategy.

### 14.4 Failure behavior and output limitations

Provider 429 responses are returned as busy/free-quota errors. Other provider HTTP failures produce a redacted status log and a configuration-appropriate message. Network failures, empty content, missing JSON fields and invalid completion types return a generic failure. A failed response is not replaced with an invented successful research note.

Prompt constraints are not guaranteed truth enforcement. The response validator checks type, presence and length, not factual entailment or an exact sentence count. The model can still introduce unsupported claims. The app labels the result as an AI draft requiring review. There is no measured precision, recall, hallucination rate or investment prediction accuracy for this component.

### 14.5 What this AI work is and is not

This is pretrained-model inference and prompt integration. It is not fine-tuning, training from scratch, forecasting, a recommendation model, a vector search system or a multi-step autonomous agent. Selecting a row with SQL supplies context, but that alone is not a full retrieval augmented generation architecture with document retrieval and source citation.

## 15 Retained MySQL and local AI workflow

### 15.1 The MySQL analytical script

vc_analytics.sql contains database/table setup, cumulative funding examples, LAG and RANK examples, percentile-based concentration, a recent-company view and the local summary table. The view uses a funding threshold derived using PERCENT_RANK and a dynamic recent-year condition. It builds a prompt description with CONCAT, COALESCE, FORMAT and CASE expressions.

The legacy recent-company condition uses the current database year minus 15. Because this is an old snapshot, its eligible rows change with calendar time even though the source data does not. A fixed, documented as-of year would be more reproducible for historical research.

The retained SQL view also contains old amount-based labels such as “Unicorn” and “Series A.” Funding does not establish valuation or a fundraising round. The deployed cloud path corrected that behavior; the legacy SQL still needs alignment before those labels are treated as valid research output.

### 15.2 Local batch model classes

- StartupRecord and DueDiligenceSummary are dataclasses grouping fields for a record and its result.
- OllamaBackend checks the local tags endpoint and sends a generation request to a local Ollama server, normally using Mistral.
- HuggingFaceBackend lazily loads a tokenizer and a CPU text-generation pipeline for falcon-rw-1b.
- LLMRouter selects Ollama when available, otherwise Hugging Face, and remembers the selected backend.
- sanitize_thesis normalizes whitespace and keeps the first two sentence-like fragments using a regular expression.

This is an example of a strategy/router abstraction and lazy loading. It does not guarantee per-request failover if an initially chosen Ollama server later fails. The regex is not a linguistically complete sentence parser, especially for abbreviations and punctuation.

### 15.3 Batch processing behavior

The legacy pipeline reads the MySQL view, caps a run at 500 records, skips IDs already present in its summary table, generates text sequentially, commits batches of two, and writes a local JSON output. Failed model calls can be saved as explicit failure text marked with an error model identifier. The JSON file represents that run's output, not a durable synchronized database replica.

This local path has not been validated as part of the current Render deployment. Do not claim that the online button calls Ollama or that the small Render instance hosts these model weights.

## 16 Computer science concepts used

| Concept | Concrete implementation |
| --- | --- |
| Separation of concerns | Startup, analytics, inference, templates and browser behavior live in different modules |
| Application factory | create_app produces an isolated configurable Flask application |
| Dependency injection | Tests provide their database URL instead of using the developer's database |
| Connection pooling | SQLAlchemy Engine manages reusable database connections |
| Transactions and context managers | begin commits or rolls back; connect scopes a connection |
| Relational aggregation | SUM, AVG, COUNT, DISTINCT, GROUP BY and ORDER BY |
| Window functions | Active PERCENT_RANK; legacy SUM OVER, LAG and RANK examples |
| Parameter binding | Values are passed separately to text SQL |
| Allowlisting | Sort options map to three developer-controlled ORDER BY clauses |
| Generators | CSV output yields chunks without building the full output string |
| Hashing | SHA256 identifies the bundled seed; it does not encrypt it |
| Compression | gzip reduces the portable seed size |
| Serialization | JSON moves row data between Python, storage and JavaScript |
| Missing values | SQL NULL, JSON null and explicit display labels preserve absence |
| Concurrency | Threads serve requests; a lock serializes inference within one worker |
| Sliding request window | A deque tracks attempts remaining in the last 60 seconds |
| Caching | Previously generated notes avoid repeated provider calls |
| Asynchronous programming | fetch, async/await and Promise.allSettled in the browser |
| Race prevention | Revision counters reject stale asynchronous UI results |
| Debouncing | A typing pause controls search request frequency |
| Coordinate transformation | SVG maps years and funding values to screen positions |
| Object-oriented design | Dataclasses and interchangeable local inference backends |
| Defensive programming | Input bounds, finite numbers, error mapping and safe storage parsing |
| Continuous integration | Fresh-environment checks run on repository events |

### 16.1 Data structures to explain

Python dictionaries store parameter bindings and group values; a tuple-key dictionary maps market/year to cohort funding. Lists hold ordered chart series. A deque supports inexpensive removal of old attempt timestamps from the left. A lock provides mutual exclusion. Browser Maps associate visible IDs with company objects so profile opening can reuse already loaded data.

### 16.2 Concepts not to overstate

The project is a modular monolith, not microservices. It uses WSGI threads and ordinary requests, not an asynchronous Python event-loop server. SQLite uses database transactions, but there is no distributed transaction. The presence of a primary key does not mean every logical relationship has a foreign-key constraint. The application has tests, not a proof of correctness for arbitrary future inputs.

## 17 Security audit and secret handling

### 17.1 Audit outcome

On 25 October 2026, the initial audit examined 27 tracked files, six reachable commits and 48 unique reachable history blobs at the stated application baseline. It checked common provider key patterns, private-key markers, credential-bearing URLs, suspicious literal assignments, forbidden credential/runtime filenames and the available local private value. The gzip seed was decompressed for content checking. Remote refs were refreshed for the repository audit.

**No real secret was found by these checks.** The local environment file was not tracked, and known local private content did not appear in the inspected tracked files or history. Environment examples contain placeholders, while test keys are deliberately fake fixtures. Apparent matches to template-based URLs and padded test values were reviewed as false positives; detector rules were refined without suppressing exact private-value checks.

This is a scoped repository audit, not a claim that no possible secret has ever existed anywhere. It does not prove the contents of old forks, unreachable Git objects, external logs, downloaded files, provider systems or arbitrary encoded data. The scanner is a project-specific guardrail rather than a complete commercial secret detector.

### 17.2 Preventive controls added

- Ignore local environment variants, private-key files, common credential JSON names, local databases, logs and generated artifacts.
- Keep `.env.example` as an explicitly permitted placeholder file.
- Run `scripts/check_secrets.py --staged` from a local pre-commit hook.
- Scan reachable history in CI after checking out full Git history.
- Test the detector using synthetic strings assembled only in memory.
- Report rule names and locations without printing matched values.
- Retain GROQ_API_KEY in Render's private environment configuration, with sync:false in the Blueprint.

Local hooks are not installed automatically in every future clone. A new clone must configure core.hooksPath. CI cannot compare against a private local password that is not present in its environment; its generic patterns and filename checks still run. A failed CI check occurs after a push and therefore is not a substitute for local pre-commit checks or provider push protection.

### 17.3 Application protections

Bound SQL values reduce injection risk; literal wildcard escaping makes search predictable; text-based DOM rendering prevents model output from becoming HTML; CSV formula prefixes reduce spreadsheet execution risks; request size and type checks reject malformed inputs; and provider credentials are used only on the server. Logs do not intentionally print the bearer key or raw provider error text in the hosted inference path.

The app does not implement login, per-user authorization, a global web application firewall, a full Content Security Policy, or encrypted browser-note storage. Public AI access is rate-limited but not user-authenticated. Do not put confidential personal/company data into this public demo without changing that design.

### 17.4 If a real secret is exposed later

Stop using it and revoke or rotate it at the issuing service first. Remove it from the working copy and future commits. Then assess reachable history, cached copies, forks, logs and artifacts with the repository owner. Deleting a file in a new commit does not remove its earlier versions. History rewriting changes commit identities and needs coordination; do not force-push a rewrite casually. GitHub's official remediation guidance is listed in section 26.

## 18 Testing and continuous integration

### 18.1 Application regression coverage

The 19 application tests cover these behaviors:

1. Landing, workspace, methodology and static assets respond; missing API routes produce JSON errors.
2. All-company counts and disclosed-funding counts differ correctly.
3. Shared filters produce consistent analytics and directory selections.
4. Missing founding years in a series carry the cumulative total forward.
5. Unknown-country records remain in the concentration ranking population.
6. Percent signs and quote-based inputs behave as literal search values.
7. Pagination preserves the requested deterministic ordering.
8. Research search is applied before the fifty-result limit, reaching records outside the unfiltered top fifty.
9. Invalid numeric bounds and sorts produce validation errors.
10. Empty selections return finite, browser-compatible JSON.
11. CSV exports honor filters and protect formula-like names.
12. No illustrative AI summaries are injected; undisclosed funding remains null.
13. Invalid generation types and oversized bodies are rejected.
14. Valid generation is cached, key whitespace is trimmed and funding is not labelled as valuation.
15. Provider quota errors do not create fake notes.
16. Provider failures do not echo credentials or raw exception strings to the client.
17. A missing key leaves data analytics usable.
18. The sixth new generation attempt is blocked while existing cached notes remain retrievable.
19. A founding-year filter excludes records without that year.

### 18.2 Secret-guard checks

Six additional tests check provider-pattern detection without echoing values, exact local private-value matching, safe placeholders/template URLs, padded dummy fixtures, blocked private filenames and decompression before scanning. The complete suite therefore contains **25 tests** after the security work in this report.

### 18.3 Test isolation and mocks

Each application test creates a temporary SQLite database with a small controlled fixture, injects its URL into a fresh application, and disposes connections before cleanup. Provider calls are mocked, so these tests do not spend inference quota or depend on the internet. Small fixtures make expected sums, ranks and null behavior explainable.

Mocks prove the application's behavior for controlled responses; they do not prove provider uptime or model quality. Live browser checks separately verified generation, copy/save and CSV download in the deployed version during the implementation work. Desktop and phone layouts were visually inspected. There is no claimed code-coverage percentage or MySQL integration test run.

### 18.4 CI pipeline

GitHub Actions runs on pushes and pull requests, checks out full history, configures Python 3.12 and Node 22, installs the web requirements, scans for secrets, runs unittest discovery and checks JavaScript syntax with Node. A passing syntax check does not exercise browser interactions. CI currently does not run an automated browser end-to-end suite, a vulnerability scanner or production load tests.

## 19 Performance and scalability

### 19.1 Current performance choices

The web application executes SQL directly rather than loading the dataset into pandas for every request. The server returns one page of directory rows at a time, uses indexes for supported access paths, streams exports, limits chart series and caches generated notes. The browser debounces searches and loads independent panels concurrently. Heavy torch/model dependencies are excluded from the web build.

### 19.2 Approximate complexity

Let N be matching company records, G be grouped cohort rows, M be displayed markets and Y be the founding-year span. A full aggregation generally inspects a relevant set of rows, with details depending on indexes and the query plan. Percentile ranking typically requires sorting the funded population. Python cohort mapping is approximately O(G + M times Y), with M capped at five. CSV serialization is linear in exported rows. Leading-wildcard name search may inspect many names. Large OFFSET values can become inefficient even when a page is small.

These are algorithmic expectations, not benchmark measurements. Actual latency depends on the database plan, CPU allocation, simultaneous requests and cold-start state.

### 19.3 Scaling changes in order

First measure slow routes and query plans. Then consider appropriate compound indexes, cache immutable aggregate results, replace expensive substring search with a dedicated indexed mechanism, and use keyset pagination for deep navigation. Introduce a persistent managed database, shared rate limits and a queued inference worker before increasing replicas. Add model/prompt/dataset versioning to cached notes.

SQLite's limited write concurrency is not the main difficulty for read-heavy historical exploration, but it matters for many concurrent note writes. More application threads do not automatically solve database or provider constraints. Increasing workers without redesigning the process-local lock can increase AI quota consumption rather than making it safely scalable.

## 20 Error handling and troubleshooting

| Symptom | Likely explanation | Appropriate check |
| --- | --- | --- |
| Loading screen after inactivity | Free instance waking | Wait about a minute and reload the live page |
| Pages load but data panels fail | Database/startup problem | Check health response and sanitized service logs |
| AI configured but generation fails | Key may be invalid, model unavailable or provider busy | Check Render secret and model setting privately; use the returned error category |
| AI note unexpectedly reappears unchanged | Cache hit for the company ID | Inspect cached flag; model settings do not invalidate existing notes |
| Notes disappear after redeploy | Ephemeral server cache | Use a previously saved browser copy or regenerate |
| Saved note absent on phone | Different origin/browser/device storage | This is expected without account synchronization |
| Local seed changes but records do not change | Investment table already populated | Use a separate fresh local database after preserving any notes needed |
| MySQL import duplicates records | Append-only importer rerun | Prepare a deliberate fresh import; do not blindly rerun into the same table |
| CSV contains an apostrophe before a formula-like name | Export safety prefix | The stored database name is unchanged |
| Percentile chart empty after narrow filters | Small or tied comparison population | Broaden the filters and inspect the definition |
| Test cleanup fails on Windows | Open SQLite connection | Close direct connections and dispose SQLAlchemy pools |
| Commit blocked by the secret guard | Private file or suspicious content staged | Unstage and inspect privately; never paste the candidate value into chat or logs |

## 21 Limitations and honest project boundaries

| Area | Current limitation | What a stronger version would require |
| --- | --- | --- |
| Data provenance | Original collection/licence details not independently established | Verified source metadata and redistribution permission |
| Freshness | Historical fixed snapshot | Licensed periodic updates and import tracking |
| Finance semantics | Funding lacks valuation and round timing | Separate funding-event and valuation data |
| Numeric storage | Floating-point values | Defined decimal or integer-minor-unit schema |
| Ingestion | Append mode and partial chunk failure | Import ledger, validation, deduplication and restart strategy |
| Database durability | Ephemeral hosted cache | Persistent database and backups |
| AI factuality | Prompted behavior can still hallucinate | Evidence checks, evaluation dataset and human review |
| AI cache | Company-ID-only identity | Prompt/model/data versioned cache |
| Rate limits | Process-local attempt window | Shared service-wide quotas and user controls |
| Accounts | No login or user-specific access | Authentication, authorization and storage ownership |
| Notebook | Device-local only | Authenticated cross-device synchronization |
| Monitoring | Basic logs and health | Structured metrics, alerts, traces and recovery procedures |
| Security checks | Pattern/exact-value guardrail | Broader secret scanning, push protection and review practices |
| Delivery | Dependencies use ranges | Locking, dependency audit and controlled upgrades |
| Testing | SQLite/mocked provider focus | Browser automation, MySQL integration and measured load tests |

The project is appropriate as an inspectable placement portfolio demo. It should not be presented as a production investment platform or a fully verified financial dataset.

## 22 Design decisions and future improvements

### 22.1 Decisions to defend

Flask keeps a small request-oriented application understandable. Server-rendered templates reduce initial UI scaffolding and let the backend own page navigation. Vanilla JavaScript is sufficient for these interactions without a client build pipeline. SVG makes the charts inspectable and removes a CDN dependency. SQLite avoids running a separate hosted database for a small historical demo. Hosted inference avoids model-loading and RAM requirements on the free web server. A separate requirements file keeps deployment lightweight.

These are context-dependent choices. A larger interactive application may benefit from a frontend framework; a multi-user service needs persistent storage and stronger access controls; a large research corpus may justify retrieval and search infrastructure. Choosing the smallest sufficient component is defensible when its limitations are explicit.

### 22.2 Prioritized roadmap

**First:** establish source provenance, align legacy misleading labels, introduce import versions and stable company identity, and add a persistent note store if continued usage needs it. **Next:** version the prompt/cache, build a factuality evaluation set, add automated browser tests and measure performance. **Later:** authenticated research notebooks, richer funding-event data, shared queues/quotas and more scalable search. These are proposed improvements, not features already built.

## 23 Demonstration and placement presentation

### 23.1 A four minute demonstration

1. Open the link in advance to wake the free service. Begin on the landing page and explain the historical scope.
2. Open the workspace. Point out total records versus funded records and explain why they differ.
3. Filter Biotechnology and United States. Show that the totals, market analysis and company directory describe the same population.
4. Explain one cohort chart point accurately: founding cohort, not calendar-year fundraising.
5. Search for a company, open its profile and distinguish missing information from zero.
6. Use Research this company, generate a note, and describe the server-to-provider path. State that the output must be reviewed.
7. Copy or save the note. Explain the difference between server cache and browser storage.
8. Export a filtered CSV or show the methodology page. Finish by naming one real tradeoff and one next improvement.

### 23.2 If the network or AI fails

Continue demonstrating the directory and SQL analysis if the provider is unavailable. Explain the actual returned error and the handling code rather than claiming a generated result. If the entire site is unavailable, use a previously captured screenshot only as a screenshot, then walk through the source, tests and architecture. Do not present saved text as a newly generated live response.

### 23.3 Explaining your contribution

Prepare a truthful account of what you implemented, what you adapted, what assistance or tools you used, and which tradeoffs you can explain. A credible project presentation demonstrates understanding and debugging ability. It does not require pretending every line was written without assistance.

For a challenge story, describe the concrete issue, how you identified it, the change and the evidence: for example, correcting a cohort definition, preventing stale search results, separating all-record counts from funded counts, or making secrets server-side. Use observed tests and outputs, not invented customer impact or percentage improvements.

### 23.4 Resume description

> Built a Flask research workspace over 49,438 historical company records with parameterized SQL analytics, shared filters, company search, CSV export and Groq-powered research notes. Added responsive SVG charts, automated regression tests and repository secret checks, and deployed the application on Render.

Use this wording only to the extent it accurately represents your contribution. Do not add accuracy or speed figures that have not been measured.

## 24 Interview questions and model answers

### 24.1 Project and architecture

**Q1 What problem does the project solve?** It makes a historical investment dataset easier to explore and converts a selected company profile into a reviewable first research draft. It supports exploration, not investment decision automation.

**Q2 What is the full stack?** Flask/Jinja and SQLAlchemy on Python, SQLite in the hosted environment, HTML/CSS/vanilla JavaScript with native SVG in the browser, and Groq for hosted inference. MySQL and local-model scripts are a separate retained workflow.

**Q3 Why use Flask?** The application has a modest set of HTTP endpoints and pages. Flask makes routing, validation boundaries and testing straightforward. I would reevaluate the framework for a different application shape rather than claim it is always best.

**Q4 Why use an app factory?** It separates construction from execution and allows tests to inject temporary database configuration. Importing the WSGI module exposes a configured app without starting the development server.

**Q5 Is it MVC?** It separates presentation, request handling and data access, but it is not a strict classical MVC implementation with ORM model classes. It is more accurately described as a modular Flask monolith.

**Q6 What happens when I open the dashboard?** Flask renders HTML, the browser loads assets, JavaScript retrieves metadata and analysis, parameterized SQL produces filtered results, and the UI renders charts and tables. AI is called only when generation is requested.

### 24.2 Database and SQL

**Q7 Why SQLite online instead of MySQL?** It keeps the free historical demo simple and avoids an additional database service. The tradeoff is ephemeral note storage and limited multi-writer scaling. MySQL remains a separate local option.

**Q8 Is SQLAlchemy the database?** No. It is the Python database integration and connection-management library. SQLite or MySQL executes and stores the relational data.

**Q9 Are you using an ORM?** Not in the current route implementation. It executes SQLAlchemy text statements and returns row mappings. The local dataclasses describe Python records, not ORM-managed entities.

**Q10 How is SQL injection prevented?** User values are bound parameters, sort orders are selected from a fixed mapping, and dynamic clauses are developer-controlled. Search separately escapes LIKE wildcard characters for literal matching.

**Q11 What is the difference between GROUP BY and a window?** GROUP BY collapses rows into aggregate groups. A window evaluates values across a related ordered set while preserving the rows produced by that query stage. The percentile CTE uses a window before outer aggregation.

**Q12 Explain the cumulative chart.** SQL groups lifetime funding by market and founding year; the hosted Python route accumulates those groups across a complete year range. A missing cohort contributes zero and carries the running total forward.

**Q13 What is PERCENT_RANK?** For more than one row it is rank minus one divided by row count minus one. Ties share rank, which means a 0.99 threshold need not select exactly one percent of the population.

**Q14 Why include unknown countries before ranking?** Excluding them would change the percentile population. A highly funded unknown-country record should affect the funding distribution and can then be grouped under Unknown.

**Q15 Why is missing funding not zero?** Missing means not disclosed in this dataset; zero is an actual numeric observation. Replacing missing with zero would distort averages and interpretation.

**Q16 What indexes exist?** Market, country, founding year and funding amount. They should be evaluated against query plans; leading-wildcard name search still has different indexing needs.

**Q17 What makes pagination deterministic?** Each sort includes id as a secondary key so equal primary sort values have a consistent order. OFFSET pagination is simple but can become costly at depth.

**Q18 How would you improve the schema?** Add stable source identities, import metadata, appropriate exact numeric types and enforced relationships. Introduce event-level tables only when the source actually provides event-level evidence.

### 24.3 Data engineering

**Q19 Why chunk the CSV?** It reduces peak intermediate DataFrame memory during cleaning and MySQL ingestion. The seed exporter still collects final rows, so I would not describe every stage as constant-memory streaming.

**Q20 What cleaning is performed?** Header normalization, selected columns, trimmed text, numeric funding cleanup, founding-year extraction/bounds, nullable values, date parsing and removal of rows missing both name and funding.

**Q21 Is the importer idempotent?** The MySQL append importer is not; a repeat can duplicate records. SQLite seed preparation avoids re-appending to an already populated table, which is a narrower property.

**Q22 How do you handle failed chunks?** They are logged and skipped; counters distinguish successful writes. A stronger pipeline would add an import ledger and deliberate retry/rollback semantics.

**Q23 Why gzip JSON?** It is a compact portable representation of the cleaned fields and is easy to restore with standard Python tools. It is compression, not encryption.

### 24.4 AI and concurrency

**Q24 Did you train the model?** No. The application uses inference from a pretrained hosted model. The work is profile selection, prompt construction, error handling, caching and UI integration.

**Q25 Is this RAG?** Not a complete RAG system. It fetches one structured database row as context; there is no vector retrieval, document chunking, embedding index or evidence-citation pipeline.

**Q26 Where is the model running?** Groq's service runs it for the online app. Ollama and Hugging Face are alternative local batch paths in the repository, not what the Render button uses.

**Q27 How is the API key protected?** It is a private server environment value used in an Authorization header. It is excluded from Git, not returned by an API and not stored in browser localStorage.

**Q28 How do you prevent duplicate provider calls?** A cached note is retrieved by company ID, and a lock serializes generation in one web process. Cache invalidation/versioning remains an explicit future improvement.

**Q29 How does the limiter work?** A deque holds attempt timestamps; entries older than 60 seconds are removed; five current attempts block another new attempt. Cached reads do not add an attempt.

**Q30 Will the limiter work across many workers?** Not as one shared budget. Each process would have its own lock/deque. A shared store or coordinated quota system is needed before scaling replicas.

**Q31 Why use finally?** The generation lock must be released even if an exception or early return occurs, otherwise later requests could remain permanently blocked.

**Q32 Can you guarantee the two-sentence response is factual?** No. The prompt requests that format and grounded behavior, while validation only checks type and size. Factuality requires evaluation and evidence checks beyond prompting.

**Q33 What does temperature mean here?** It is a sampling control that affects variation. A lower value does not guarantee deterministic or truthful output, and no exact accuracy claim follows from setting it to 0.4.

### 24.5 Browser, security and testing

**Q34 How do you prevent stale search results?** Debounced searches have revision counters; only the latest request's results update the relevant UI. This addresses response ordering without claiming to cancel every old call.

**Q35 What does Promise.allSettled provide?** It records every panel request's success or failure so a single rejected request need not prevent rendering other successful panels.

**Q36 Why native SVG?** These charts are small and can be expressed as paths and bars. SVG avoids an external chart-library dependency and allows responsive coordinate control; the tradeoff is maintaining drawing and accessibility behavior ourselves.

**Q37 How is XSS reduced?** Company and model strings are rendered as text nodes rather than executable HTML. This is a specific mitigation, not a claim that every class of browser vulnerability has been eliminated.

**Q38 Why sanitize CSV output?** Spreadsheet applications may interpret leading formula characters as executable formulas. Prefixing those exported text values reduces that risk without altering the database record.

**Q39 Does gitignore remove old secrets?** No. It affects tracking of untracked files; it does not erase existing tracked content or previous commits. Existing exposures require revocation and deliberate remediation.

**Q40 What did the secret audit prove?** The specified checks found no real secrets in the inspected tracked files and reachable history, including compressed seed content. It did not prove the absence of all secrets everywhere or replace broader security review.

**Q41 Why mock Groq?** Deterministic fake responses let the tests verify caching, limits and failures without internet dependency or quota consumption. Separate live checks confirm integration, not model accuracy.

**Q42 What is tested?** Nineteen app behaviors and six secret-guard cases. They cover important contracts and failure paths but are not full coverage, browser automation or production load testing.

### 24.6 Deployment and ownership

**Q43 Why Gunicorn instead of Flask's server?** Gunicorn is the WSGI serving process for hosted use; Flask's development server is for local development. The configured worker/thread choices reflect the small deployment and limiter design.

**Q44 What happens after a restart?** The seed is restored if necessary. Generated notes in the ephemeral server file can be lost; local browser copies remain on that device until removed.

**Q45 How do you deploy after a change?** Run tests and secret checks, inspect the staged diff, commit and push the intended files, verify CI and Render's deployed commit, then smoke-test pages, filters, export and one model request.

**Q46 What would you improve first?** Verify data provenance, fix remaining legacy semantics, version imports and cached notes, and add persistent storage if multi-user durability is required. Choose based on the use case rather than adding technologies for appearance.

**Q47 What is the strongest lesson from the project?** Correct interpretation is part of correctness: a chart can render perfectly while making a false claim about what its x-axis or funding amount means. Good engineering includes explicit definitions and tests for those meanings.

## 25 Glossary and last minute revision

| Term | Meaning in this project |
| --- | --- |
| API | HTTP interface through which the browser requests data or generation |
| WSGI | Interface between a Python web application and its serving process |
| ETL | Extract source data, transform it, load a target store |
| Seed | Bundled cleaned dataset used to initialize the hosted database |
| Cohort | Companies grouped by a shared founding year |
| Disclosed funding | Available total raised in the source record |
| NULL | Missing database information |
| CTE | Named query expression scoped to one SQL statement |
| Window function | Calculation across a related set of ordered query rows |
| Percentile rank | Relative rank within the selected funded population |
| Bound parameter | Value supplied separately from SQL statement structure |
| Index | Additional database structure that may improve particular access paths |
| Transaction | Unit of work with commit or rollback behavior |
| Cache | Reused stored computation, here a generated note |
| Idempotence | Repeating an operation does not produce additional unintended effects |
| Debounce | Wait for an input pause before performing an action |
| Race condition | Outcome affected by ordering of concurrent operations |
| Lock | Mutual-exclusion mechanism controlling concurrent entry |
| Deque | Double-ended queue used to remove old timestamps efficiently |
| Inference | Generating output using an existing trained model |
| Hallucination | Unsupported model-generated content presented plausibly |
| localStorage | Persistent browser-origin storage, not cross-device synchronization |
| Ephemeral filesystem | Local server files may disappear on restart/redeployment |
| CI | Automated checks triggered by repository events |
| Secret | Credential or private value that must not be published |
| SHA256 | Cryptographic content hash used here for artifact identification |
| SVG | Vector markup used to draw browser charts |

### Final revision checklist

- Explain each layer and point to its actual source file.
- Trace one filter request and one generation request end to end.
- Work through a cumulative cohort and percentile example by hand.
- Explain why 49,438 and 40,907 measure different populations.
- Distinguish hosted Groq from retained local Ollama/Hugging Face scripts.
- State that total raised is not valuation and source status is historical.
- Explain SQL binding, wildcard escaping, DOM text rendering and CSV protection.
- Explain cache invalidation, per-process limits and ephemeral storage.
- Know the test command and demonstrate a failing input producing an intentional error.
- Be honest about assistance, unmeasured performance, missing provenance and future work.
- Keep the live link ready and use the deployment procedure below for future updates.

## 26 References and evidence

The repository itself is the primary evidence for implementation. In particular, inspect webapp.py for setup and errors, analytics.py for actual active SQL, cloud_ai.py for live inference, static/app.js for state/visualization, the two test modules for regression scope, and render.yaml for serving commands. The SHA and seed fingerprint near the beginning make the inspected baseline identifiable.

Official operational references checked on 25 October 2026:

- Render free service behavior: https://render.com/docs/free
- Render linked-branch, manual and CI-aware deployments: https://render.com/docs/deploys
- Groq supported model identifiers: https://console.groq.com/docs/models
- Groq request quotas: https://console.groq.com/docs/rate-limits
- GitHub guidance for exposed credentials and repository history: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

Useful primary documentation for further study:

- Flask application factories: https://flask.palletsprojects.com/en/stable/patterns/appfactories/
- SQLAlchemy engine/connection tutorial: https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html
- SQLite window functions: https://www.sqlite.org/windowfunctions.html
- Python threading: https://docs.python.org/3/library/threading.html
- Python deque: https://docs.python.org/3/library/collections.html#collections.deque
- MDN Promise.allSettled: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/allSettled
- MDN localStorage: https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage

The free hosting description is operational guidance, not a price guarantee. Render documents sleep after 15 minutes without traffic, approximately a minute to wake, and an ephemeral local filesystem. Provider plans and supported models can change; review the console before a new deployment.

## 27 Deployment after changes

This is the final operational chapter. Use it every time you change source, configuration or the seed. The existing site is already linked to the repository; ordinary code updates do not require creating another Render service or adding an API key to Git.

### 27.1 Prepare a local environment

From the repository directory in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-web.txt
git config core.hooksPath .githooks
$env:DATABASE_URL = 'sqlite:///cloud.db'
python app.py
```

Open http://localhost:5000. Preparation will initialize a missing file-based SQLite database. Keep a real AI key only in your private local environment file or process environment; copy variable names from .env.example, not a real credential into source. Never include the key in a browser URL, screenshot or report. Stop the development server before continuing if the terminal is still occupied.

### 27.2 Make and verify the change

Change the relevant template, static file or Python module. If changing financial meanings or query behavior, update methodology and regression tests as well. Run:

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
python scripts/check_secrets.py --history
git diff --check
git status --short
git diff --stat
```

Check the local landing page, dashboard and methodology page. Test the interaction affected by your change. For UI work, inspect both a desktop viewport and a phone viewport, including long funding values, forms, tables and dialogs. A Python test pass alone does not validate the rendered UI.

### 27.3 Stage deliberately and inspect before publishing

Stage named source files or directories that belong to the change. For example:

```powershell
git add templates/landing.html static/style.css
git diff --cached --stat
git diff --cached --name-only
python scripts/check_secrets.py --staged
```

The file names above are examples; stage the actual files you changed. Do not stage a real environment file, database, key file, logs, generated artifact folder or credential screenshot. Review a staged diff privately in your editor. Avoid commands that print all local environment variables or credential contents into shared logs.

If the guard flags a staged file, stop and unstage that specific file:

```powershell
git restore --staged -- path-to-the-flagged-file
```

Inspect and correct it privately, then rerun the check. Do not bypass the hook with --no-verify just to finish a deployment. If an actual live credential has already reached the remote, follow the revocation/remediation procedure in section 17 before proceeding.

### 27.4 Commit and push the approved update

```powershell
git commit -m "Describe the concrete change"
git push origin main
```

The local hook scans staged content during commit. The current deployment branch is main; use a branch and pull request instead if the repository's review policy changes. A push to main changes the public repository and can trigger the live service, so review the staged selection before committing.

### 27.5 Check GitHub Actions and Render

1. Open the repository's Actions page and inspect the Application checks run for the new commit.
2. Confirm secret checks, Python tests and JavaScript syntax checks all succeed.
3. Open the existing vc-funding-analytics web service in Render.
4. Verify that the deployment uses the intended commit and reaches Live.
5. Inspect sanitized build/startup logs if it fails. Do not copy credentials or full environment dumps into an issue or chat.

The linked service has auto-deployed commits in this project. Render can instead be configured to deploy only after CI passes. Unless that setting is verified, do not assume a failing CI check prevents an On Commit deployment. If automatic deployment is disabled, use Manual Deploy for the intended latest commit rather than creating a duplicate service.

### 27.6 Confirm runtime settings

Keep the Free service plan selected if the objective remains a free interview demo. The configured build command is:

```text
pip install -r requirements-web.txt
```

The configured start command is:

```text
python prepare_cloud_db.py && gunicorn --workers 1 --threads 4 --timeout 90 --bind 0.0.0.0:$PORT app:app
```

In Render, DATABASE_URL should remain `sqlite:///cloud.db` for this setup, GROQ_MODEL should identify an available model, and GROQ_API_KEY should be entered only in the private environment settings. render.yaml lists the key name with sync:false; it must never contain the actual secret value. The configured health path is `/api/health`.

A secret rotation normally means replacing the private Render value and redeploying/restarting as needed. It does not mean committing the new key. Do not change to multiple workers without revisiting the lock, quota and cache design.

### 27.7 Smoke test the deployed application

Open https://vc-funding-analytics.onrender.com and verify:

1. The intended landing page appears and the market preview loads.
2. `/dashboard` loads real totals and charts without browser errors.
3. A known market/country filter changes analytics and directory consistently.
4. Searching a known company opens its historical profile.
5. A filtered CSV download contains the intended population.
6. One research request either generates a real note or clearly returns an actual provider error. Avoid repeatedly consuming quota unnecessarily.
7. Copy and local save work if those flows were affected.
8. `/methodology` still explains the displayed analysis accurately.
9. A phone layout has no page-wide horizontal overflow or clipped key figures.
10. `/api/health` reports database availability. Remember that ai_configured alone is not a live inference test.

### 27.8 If you changed the dataset

Use the full local ETL environment because the exporter needs pandas and NumPy:

```powershell
python export_cloud_seed.py 'C:\path\to\investments_VC.csv'
```

Validate row counts, missing values, categories and finance semantics; verify that redistribution of the new source is appropriate. Scan the compressed seed and stage it explicitly. Update static coverage statements in documentation and methodology if counts or year ranges change.

For a local populated database, test the new seed in a separate database file rather than deleting a file that might contain notes you need. A new hosted deployment normally restores from the bundled seed on its fresh ephemeral filesystem, but the preparation code itself does not overwrite a non-empty investment table. Stable IDs and cache invalidation need particular attention when the source order changes.

### 27.9 Recovery and interview readiness

If a release fails, inspect its logs and the intended commit first. Render supports deployment history and rollback within the plan's available limits; select a known working version only when needed, then fix the source and redeploy deliberately. Do not delete the service or database as a first troubleshooting step.

Before an interview, open the live site approximately one minute early because the free instance may be asleep. Retain a screenshot and the report for discussion if network access fails, but clearly distinguish offline evidence from a live demonstration. Confirm your key is still private, the current model is available, and the project description you use matches the version you are showing.
