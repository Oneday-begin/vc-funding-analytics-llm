# Venture Atlas

A research workspace for a historical venture funding dataset. The app connects
an editorial landing page, SQL analytics, a searchable company directory, and
on-demand AI research notes.

**Live app:** https://vc-funding-analytics.onrender.com

## What you can do

- Filter every analytics panel and the directory by market, country, recorded
  status, and founding year. Filter URLs can be bookmarked or shared.
- Compare lifetime funding across founding cohorts, market allocation, company
  statuses, and the countries represented in the top funding percentile.
- Search all company records, inspect a profile, paginate and sort results, and
  export the filtered directory to CSV.
- Generate a research note from a historical profile with Groq. Copy it or save
  it in this browser. No account is needed.
- Read the source definitions and limitations at `/methodology`.

## Run locally

Requires Python 3.12. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-web.txt
$env:DATABASE_URL = 'sqlite:///cloud.db'
python app.py
```

Open http://localhost:5000. SQLite is initialized from the bundled cleaned seed
automatically. Do not commit `cloud.db` or `.env`.

For live generation, set `GROQ_API_KEY` privately in your environment. The optional
`GROQ_MODEL` defaults to `openai/gpt-oss-20b`. Without a key, the data and analytics
still work and previously cached notes can still be retrieved.

For MySQL, omit `DATABASE_URL` and set the `DB_*` variables in `.env` using
`.env.example`. The original `vc_analytics.sql`, `etl_pipeline.py`, and
`ai_due_diligence.py` support the separate local MySQL/Ollama workflow. Install
`requirements.txt` for that workflow; it includes large model dependencies that
the hosted web app does not need. Set up the schema and summary table before
running against MySQL. The CSV importer **appends** records; use an empty target
table for a fresh import instead of repeatedly importing the same file.

```powershell
python etl_pipeline.py --csv 'C:\path\to\investments_VC.csv'
```

## Architecture

```text
app.py                     WSGI entry point
webapp.py                  App factory, configuration, pages, HTTP errors
analytics.py               Bound-parameter SQL queries, filters, search, CSV
cloud_ai.py                Live inference, cached notes, generation limits
prepare_cloud_db.py        Repeatable SQLite seed restoration and indexes
templates/                 Jinja landing, dashboard, methodology, error pages
static/                    Shared styles, native SVG charts, browser interactions
tests/test_app.py          Isolated database and mocked inference regression checks
data/investments.json.gz   Cleaned six-field snapshot; no credentials
render.yaml                Free Render deployment configuration
```

The web app uses SQLAlchemy directly rather than materializing query results in
pandas. The ETL tools continue to use pandas for cleaning. Native SVG charts have
no external chart-library dependency. Untrusted dataset and model text is inserted
with DOM text methods. SQL filter values are bound parameters, sort orders are
allowlisted, and CSV text cells are protected against spreadsheet formula execution.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/metadata` | Coverage and filter options |
| `GET /api/stats` | All matching records vs. funded records and totals |
| `GET /api/funding-trends` | Lifetime funding across founding cohorts |
| `GET /api/top-markets` | Funding-ranked markets |
| `GET /api/funding-by-status` | Historical status distribution |
| `GET /api/country-concentration` | Countries in the top funding percentile |
| `GET /api/companies` | Searchable, paginated company directory |
| `GET /api/companies/<id>` | One historical profile |
| `GET /api/companies/export.csv` | Filtered CSV export |
| `GET /api/startups` | Funded company choices for the research desk |
| `POST /api/generate-thesis` | Generate/cache a note from `{ "startup_id": 123 }` |
| `GET /api/ai-summaries` | Genuine generated notes only |
| `GET /api/health` | Database health and AI configuration availability |

Analytics and directory endpoints accept `market`, `country`, `status`,
`year_from`, and `year_to`. The directory also supports `q`, `page`, `per_page`
(1–100), and `sort` (`funding_desc`, `name_asc`, `year_desc`). Research search
is independent of the dashboard filters.

## Checks

```text
python -m unittest discover -s tests -v
node --check static/app.js
python scripts/check_secrets.py --history
```

Tests use isolated temporary SQLite databases and mocked provider responses;
they do not call Groq or spend inference quota. GitHub Actions runs these checks
on pushes and pull requests.

Install the local staged-secret guard once per clone with
`git config core.hooksPath .githooks`. The hook checks staged files before a
commit; CI also checks reachable history. Neither replaces careful review or
provider push protection. Keep secrets in private environment configuration.

For a comprehensive architecture explanation, interview questions, and the
end-to-end update/deployment procedure, read [the placement report](PLACEMENT_REPORT.md).

## What the numbers mean

The bundled seed has 49,438 records, including 40,907 with positive disclosed
funding. Known founding years span 1902–2014. This does **not** date the snapshot.
The original CSV's collection date, full provenance, and source licence have not
been independently established in this repository. It is a portfolio research
dataset, not an audited market feed.

Total funding is not valuation. Founding cohorts are not annual funding flows.
Recorded status is not current status. The percentile query includes unknown
countries in its ranking population. Ties can produce a cohort other than exactly
one percent; small populations may yield no top-percentile records.

AI notes use only the selected profile, without web research or independent fact
verification. They can be wrong. Do not treat them as investment advice.

## Hosting

See [DEPLOYMENT.md](DEPLOYMENT.md). Render's free instance can take about a minute
to wake after inactivity. The bundled dataset survives restarts through seed
restoration, while generated server notes can reset. Locally saved notes persist
only in the current browser and do not sync between devices.
