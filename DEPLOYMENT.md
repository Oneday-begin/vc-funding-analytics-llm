# Free interview deployment

The hosted dashboard runs Flask and its real SQL analytics on Render's Free plan.
It restores 49,438 cleaned historical startup records into SQLite at startup.
Live investment theses are generated on demand by Groq; PyTorch and Ollama are
kept out of the small web server. The original local MySQL/Ollama scripts remain available.

## Deploy

1. Open https://dashboard.render.com/select-repo?type=blueprint and select
   `Oneday-begin/vc-funding-analytics-llm` (or use the Render Blueprint flow).
2. Review `render.yaml`: the web service must say **Free**.
3. Create a free Groq account at https://console.groq.com and create an API key.
   Enter it only in Render's `GROQ_API_KEY` secret field. Never commit it or put it in frontend code.
4. Deploy. Open the URL Render provides and check `/api/health`.
5. Select a startup and click **Generate AI thesis** to verify the live model.

The model is configured with `GROQ_MODEL`, default `llama-3.3-70b-versatile`.
If your Groq account no longer offers that model, choose an available chat model
in Groq's console and update this environment variable.

## Free plan behavior

- Render sleeps after 15 minutes without traffic. Open the site about a minute
  before the interview so it can wake up.
- Base data is restored on each restart. Newly generated theses are cached until
  the service restarts or sleeps; they can be generated again afterwards.
- Generation is limited to five new requests per minute, one at a time. Groq has
  its own free quota. Keep Groq on the Free plan and Render on Free compute.
- Saved summaries and illustrative examples are labelled separately from live
  generation. The data is historical, not a live funding feed.
- The free workspace's included hours are shared with your other Render services.
  Review the workspace's remaining hours if other demos run in the same account.

## Refresh the seed

Run `python export_cloud_seed.py <path-to-investments_VC.csv>` and commit only
`data/investments.json.gz`. This uses the existing ETL cleaning and exports six
investment fields; it includes no database credentials or environment files.

## Run the hosted configuration locally

Install `requirements-web.txt`, run `python prepare_cloud_db.py`, and set
`DATABASE_URL=sqlite:///cloud.db`. Optionally set `GROQ_API_KEY` in your local
environment, then run `python app.py`. The default without `DATABASE_URL` still
connects to the original MySQL configuration.
