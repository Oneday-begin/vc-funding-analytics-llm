"""Parameterized analytics and company exploration over the historical snapshot."""
import csv
import io
import math

from flask import Response, abort, jsonify, request, stream_with_context
from sqlalchemy import text


def integer_arg(name, default, minimum, maximum):
    value = request.args.get(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        abort(400, f"{name} must be a whole number.")
    if not minimum <= parsed <= maximum:
        abort(400, f"{name} must be between {minimum} and {maximum}.")
    return parsed


def filters(search=False):
    clauses, params = ["1=1"], {}
    for key, column in (("market", "market"), ("country", "country_code"), ("status", "status")):
        value = request.args.get(key, "").strip()
        if value:
            if len(value) > 255:
                abort(400, f"{key} is too long.")
            clauses.append(f"{column} = :{key}")
            params[key] = value
    lower = integer_arg("year_from", None, 1900, 2030)
    upper = integer_arg("year_to", None, 1900, 2030)
    if lower and upper and lower > upper:
        abort(400, "The first founding year must be before the last.")
    for key, value, op in (("year_from", lower, ">="), ("year_to", upper, "<=")):
        if value is not None:
            clauses.append(f"founded_year {op} :{key}")
            params[key] = value
    if search:
        query = request.args.get("q", "").strip()
        if len(query) > 100:
            abort(400, "Search must be 100 characters or fewer.")
        if query:
            clauses.append("LOWER(name) LIKE :query ESCAPE '!'")
            params["query"] = "%" + query.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    return " AND ".join(clauses), params


def records(engine, sql, params=None):
    with engine.connect() as conn:
        result = [dict(row) for row in conn.execute(text(sql), params or {}).mappings()]
    for row in result:
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                row[key] = None
    return result


def register_analytics(app, engine):
    @app.get("/api/metadata")
    def metadata():
        row = records(engine, """SELECT COUNT(*) AS total_records,
            SUM(CASE WHEN funding_total_usd > 0 THEN 1 ELSE 0 END) AS funded_records,
            COUNT(founded_year) AS dated_records, MIN(founded_year) AS first_year,
            MAX(founded_year) AS last_year, COUNT(DISTINCT market) AS markets,
            COUNT(DISTINCT country_code) AS countries FROM startup_investments""")[0]
        row.update(
            market_options=[r["market"] for r in records(engine, "SELECT DISTINCT market FROM startup_investments WHERE market IS NOT NULL ORDER BY market")],
            country_options=[r["country_code"] for r in records(engine, "SELECT DISTINCT country_code FROM startup_investments WHERE country_code IS NOT NULL ORDER BY country_code")],
            status_options=[r["status"] for r in records(engine, "SELECT DISTINCT status FROM startup_investments WHERE status IS NOT NULL ORDER BY status")],
            source="Project investments_VC.csv snapshot", kind="historical",
        )
        return jsonify(row)

    @app.get("/api/stats")
    def stats():
        where, params = filters()
        row = records(engine, f"""SELECT COUNT(*) AS total_records,
            SUM(CASE WHEN funding_total_usd > 0 THEN 1 ELSE 0 END) AS total_startups,
            ROUND(COALESCE(SUM(funding_total_usd),0)/1e9,2) AS total_funding_bn,
            COUNT(DISTINCT market) AS total_markets, COUNT(DISTINCT country_code) AS total_countries,
            MIN(founded_year) AS first_year, MAX(founded_year) AS last_year
            FROM startup_investments WHERE {where}""", params)[0]
        row["total_startups"] = row["total_startups"] or 0
        for field in ("market", "country_code"):
            top = records(engine, f"""SELECT {field} AS name FROM startup_investments
                WHERE {where} AND {field} IS NOT NULL AND funding_total_usd > 0
                GROUP BY {field} ORDER BY SUM(funding_total_usd) DESC, {field} LIMIT 1""", params)
            row["top_market" if field == "market" else "top_country"] = top[0]["name"] if top else None
        return jsonify(row)

    @app.get("/api/top-markets")
    def top_markets():
        where, params = filters()
        limit = integer_arg("limit", 15, 1, 100)
        return jsonify(records(engine, f"""SELECT market, COUNT(*) AS startup_count,
            ROUND(SUM(funding_total_usd)/1e9,3) AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6,2) AS avg_funding_mn,
            COUNT(DISTINCT country_code) AS countries_represented FROM startup_investments
            WHERE {where} AND market IS NOT NULL AND funding_total_usd > 0
            GROUP BY market ORDER BY SUM(funding_total_usd) DESC, market LIMIT :limit""", {**params, "limit": limit}))

    @app.get("/api/funding-trends")
    def funding_trends():
        where, params = filters()
        selected = [x.strip() for x in request.args.get("markets", "").split(",") if x.strip()]
        if len(selected) > 5:
            abort(400, "Compare up to five markets at a time.")
        if selected:
            for i, market in enumerate(selected):
                params[f"m{i}"] = market
            where += " AND market IN (" + ",".join(f":m{i}" for i in range(len(selected))) + ")"
        top = records(engine, f"""SELECT market FROM startup_investments
            WHERE {where} AND market IS NOT NULL AND founded_year IS NOT NULL AND funding_total_usd > 0
            GROUP BY market ORDER BY SUM(funding_total_usd) DESC, market LIMIT 5""", params)
        if not top:
            return jsonify(labels=[], datasets=[])
        rows = records(engine, f"""SELECT market, founded_year,
            SUM(funding_total_usd)/1e6 AS yearly_funding_mn FROM startup_investments
            WHERE {where} AND founded_year IS NOT NULL AND funding_total_usd > 0
            GROUP BY market, founded_year ORDER BY founded_year""", params)
        names = [r["market"] for r in top]
        values = {(r["market"], int(r["founded_year"])): r["yearly_funding_mn"] for r in rows if r["market"] in names}
        years_present = [year for _, year in values]
        labels = list(range(min(years_present), max(years_present) + 1))
        colors = ["#275e4c", "#ba6543", "#737c9d", "#b49b5a", "#4f8e9a"]
        datasets = []
        for name, color in zip(names, colors):
            total, data = 0, []
            for year in labels:
                total += float(values.get((name, year), 0))
                data.append(round(total, 2))
            datasets.append(dict(label=name, data=data, borderColor=color))
        return jsonify(labels=labels, datasets=datasets, definition="Cumulative lifetime funding grouped by company founding year; not funding raised in each calendar year.")

    @app.get("/api/funding-by-status")
    def funding_status():
        where, params = filters()
        return jsonify(records(engine, f"""SELECT COALESCE(status,'unknown') AS status,
            COUNT(*) AS count, ROUND(SUM(funding_total_usd)/1e9,3) AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6,2) AS avg_funding_mn
            FROM startup_investments WHERE {where} AND funding_total_usd > 0
            GROUP BY status ORDER BY SUM(funding_total_usd) DESC""", params))

    @app.get("/api/country-concentration")
    def concentration():
        where, params = filters()
        return jsonify(records(engine, f"""WITH ranked AS (
            SELECT country_code, status, market, funding_total_usd,
            PERCENT_RANK() OVER (ORDER BY funding_total_usd) AS pct_rank
            FROM startup_investments WHERE {where} AND funding_total_usd > 0)
            SELECT COALESCE(country_code,'Unknown') AS country_code,
            COUNT(*) AS startup_count, ROUND(SUM(funding_total_usd)/1e9,3) AS total_funding_bn,
            ROUND(AVG(funding_total_usd)/1e6,2) AS avg_funding_mn, COUNT(DISTINCT market) AS distinct_markets
            FROM ranked WHERE pct_rank >= 0.99 GROUP BY country_code
            ORDER BY SUM(funding_total_usd) DESC LIMIT 10""", params))

    orders = {"funding_desc": "funding_total_usd DESC, id", "name_asc": "name ASC, id",
              "year_desc": "founded_year DESC, id"}

    @app.get("/api/companies")
    def companies():
        where, params = filters(search=True)
        page = integer_arg("page", 1, 1, 100000)
        size = integer_arg("per_page", 12, 1, 100)
        order = request.args.get("sort", "funding_desc")
        if order not in orders:
            abort(400, "Unknown sort order.")
        total = records(engine, f"SELECT COUNT(*) AS total FROM startup_investments WHERE {where}", params)[0]["total"]
        rows = records(engine, f"""SELECT id, name, market, country_code, status, founded_year, funding_total_usd
            FROM startup_investments WHERE {where} ORDER BY {orders[order]} LIMIT :limit OFFSET :offset""",
                       {**params, "limit": size, "offset": (page - 1) * size})
        return jsonify(records=rows, total=total, page=page, per_page=size, pages=math.ceil(total / size))

    @app.get("/api/companies/<int:company_id>")
    def company(company_id):
        rows = records(engine, "SELECT id,name,market,country_code,status,founded_year,funding_total_usd FROM startup_investments WHERE id=:id", {"id": company_id})
        if not rows:
            abort(404, "Company not found.")
        return jsonify(rows[0])

    @app.get("/api/companies/export.csv")
    def export_companies():
        where, params = filters(search=True)
        fields = ["name", "market", "country_code", "status", "founded_year", "funding_total_usd"]

        def generate():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(fields)
            yield output.getvalue()
            with engine.connect() as conn:
                result = conn.execution_options(stream_results=True).execute(text(
                    f"SELECT {','.join(fields)} FROM startup_investments WHERE {where} ORDER BY funding_total_usd DESC, id"), params)
                for row in result:
                    output.seek(0)
                    output.truncate()
                    writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for v in row])
                    yield output.getvalue()
        return Response(stream_with_context(generate()), mimetype="text/csv", headers={"Content-Disposition": 'attachment; filename="venture-atlas-companies.csv"'})

    @app.get("/api/startups")
    def startup_options():
        where, params = filters(search=True)
        return jsonify(records(engine, f"""SELECT id,name,market,funding_total_usd FROM startup_investments
            WHERE {where} AND name IS NOT NULL AND funding_total_usd > 0
            ORDER BY funding_total_usd DESC, id LIMIT 50""", params))

    @app.get("/api/ai-summaries")
    def summaries():
        limit = integer_arg("limit", 20, 1, 100)
        params = {"limit": limit}
        where = "1=1"
        if request.args.get("market"):
            where += " AND market=:market"
            params["market"] = request.args["market"]
        rows = records(engine, f"""SELECT startup_id,startup_name,market,funding_tier,maturity_stage,
            country_code,investment_thesis,model_used,generated_at FROM ai_due_diligence_summaries
            WHERE {where} ORDER BY generated_at DESC, startup_id DESC LIMIT :limit""", params)
        return jsonify(source=engine.dialect.name, records=rows)
