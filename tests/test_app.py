"""Regression checks for analytics semantics, search/export, and cloud inference."""
import csv
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from webapp import create_app


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = str(Path(self.directory.name) / "test.db")
        with sqlite3.connect(self.database) as conn:
            conn.executescript("""
                CREATE TABLE startup_investments(id INTEGER PRIMARY KEY, name TEXT, market TEXT,
                    funding_total_usd REAL, status TEXT, country_code TEXT, founded_year INTEGER);
                CREATE TABLE ai_due_diligence_summaries(startup_id INTEGER PRIMARY KEY,
                    startup_name TEXT, market TEXT, funding_tier TEXT, maturity_stage TEXT,
                    country_code TEXT, investment_thesis TEXT, model_used TEXT, generated_at TEXT);
            """)
            conn.executemany("INSERT INTO startup_investments VALUES (?,?,?,?,?,?,?)", [
                (1,"Alpha Bio","Biotechnology",1e8,"operating","USA",2000),
                (2,"Beta Mobile","Mobile",5e7,"acquired","IND",2001),
                (3,"Gamma Bio","Biotechnology",2e8,"closed","USA",2002),
                (4,"Undisclosed","Mobile",None,None,None,None),
                (5,"100% Tools","Software",1e7,"operating","USA",2004),
                (6,"=1+1","Software",2e6,"operating","CAN",2010),
                (7,"Unknown Country","Biotechnology",1e9,"operating",None,2005),
                (8,"Zeta Bio","Biotechnology",1e8,"operating","GBR",2000),
            ])
        conn.close()
        self.app = create_app({"TESTING": True, "DATABASE_URL": "sqlite:///" + self.database, "AUTO_PREPARE_DB": False})
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["database"].dispose()
        self.directory.cleanup()

    def test_landing_workspace_methodology_and_not_found(self):
        for url in ("/", "/dashboard", "/methodology", "/static/style.css", "/static/app.js"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            response.close()
        self.assertEqual(self.client.get("/missing").status_code, 404)
        missing = self.client.get("/api/missing")
        self.assertEqual(missing.status_code, 404)
        self.assertIn("error", missing.json)

    def test_counts_include_undisclosed_companies(self):
        stats = self.client.get("/api/stats").json
        self.assertEqual(stats["total_records"], 8)
        self.assertEqual(stats["total_startups"], 7)
        self.assertEqual(stats["total_funding_bn"], 1.46)
        self.assertEqual(self.client.get("/api/metadata").json["dated_records"], 7)

    def test_shared_filters_and_directory_agree(self):
        query = "?market=Biotechnology&country=USA&year_from=2001"
        stats = self.client.get("/api/stats" + query).json
        companies = self.client.get("/api/companies" + query).json
        markets = self.client.get("/api/top-markets" + query).json
        self.assertEqual(stats["total_records"], companies["total"])
        self.assertEqual(stats["total_records"], 1)
        self.assertEqual(companies["records"][0]["name"], "Gamma Bio")
        self.assertEqual(markets[0]["total_funding_bn"], .2)

    def test_cumulative_cohorts_carry_forward_missing_years(self):
        data = self.client.get("/api/funding-trends?markets=Biotechnology").json
        self.assertEqual(data["labels"], [2000,2001,2002,2003,2004,2005])
        self.assertEqual(data["datasets"][0]["data"], [200,200,400,400,400,1400])
        self.assertIn("not funding raised", data["definition"])

    def test_country_ranking_includes_unknown_country(self):
        data = self.client.get("/api/country-concentration").json
        self.assertEqual(data[0]["country_code"], "Unknown")
        self.assertEqual(data[0]["total_funding_bn"], 1)

    def test_percent_and_quotes_are_literal_search_values(self):
        self.assertEqual(self.client.get("/api/companies?q=%25").json["total"], 1)
        self.assertEqual(self.client.get("/api/companies?q=%27%20OR%201%3D1--").json["total"], 0)
        self.assertEqual(self.client.get("/api/companies?market=%27%20OR%201%3D1--").json["total"], 0)

    def test_search_and_pagination_preserve_sort_order(self):
        response = self.client.get("/api/companies?q=Bio&per_page=1&page=2&sort=name_asc").json
        self.assertEqual(response["total"], 3)
        self.assertEqual(response["pages"], 3)
        self.assertEqual(response["records"][0]["name"], "Gamma Bio")
        self.assertEqual(self.client.get("/api/startups?q=Beta").json[0]["id"], 2)

    def test_research_search_is_not_limited_to_unfiltered_top_fifty(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany("INSERT INTO startup_investments VALUES (?,?,?,?,?,?,?)", [
                (100+i, f"Larger company {i}", "Software", 3e9, "operating", "USA", 2010)
                for i in range(60)
            ])
        conn.close()
        self.assertNotIn(2, [row["id"] for row in self.client.get("/api/startups").json])
        self.assertEqual(self.client.get("/api/startups?q=Beta").json[0]["id"], 2)

    def test_input_errors_are_json_and_do_not_query_invalid_limits(self):
        for url in ("/api/companies?page=0", "/api/companies?per_page=1000", "/api/companies?sort=DROP",
                    "/api/ai-summaries?limit=oops", "/api/ai-summaries?limit=-1", "/api/stats?year_from=2010&year_to=2000"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400, url)
            self.assertIn("error", response.json)

    def test_empty_filtered_selection_and_json_validity(self):
        for path in ("stats", "funding-trends", "country-concentration", "funding-by-status", "top-markets", "companies"):
            response = self.client.get("/api/" + path + "?country=NONEXISTENT")
            self.assertEqual(response.status_code, 200)
            json.loads(response.data, parse_constant=lambda value: self.fail("Invalid JSON value " + value))
        self.assertEqual(self.client.get("/api/stats?country=NONEXISTENT").json["total_funding_bn"], 0)

    def test_csv_respects_filters_and_escapes_spreadsheet_formulas(self):
        response = self.client.get("/api/companies/export.csv?country=CAN")
        rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "'=1+1")
        self.assertIn("attachment", response.headers["Content-Disposition"])

    def test_no_illustrative_summaries_are_injected(self):
        self.assertEqual(self.client.get("/api/ai-summaries").json["records"], [])
        self.assertEqual(self.client.get("/api/companies/4").json["funding_total_usd"], None)
        self.assertEqual(self.client.get("/api/companies/999").status_code, 404)

    def test_generation_input_size_and_type_validation(self):
        for body in (None, [], {"startup_id": True}, {"startup_id": "1"}, {"startup_id": -1}):
            self.assertEqual(self.client.post("/api/generate-thesis", json=body).status_code, 400)
        response = self.client.post("/api/generate-thesis", data="x"*5000, content_type="application/json")
        self.assertEqual(response.status_code, 413)

    @patch.dict(os.environ, {"GROQ_API_KEY": "  test-key  "})
    @patch("cloud_ai.requests.post")
    def test_live_generation_is_cached_and_not_mislabeled_as_valuation(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"choices": [{"message": {"content": "A sector hypothesis. A company risk."}}]}
        result = self.client.post("/api/generate-thesis", json={"startup_id": 1})
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json["cached"])
        self.assertIn("disclosed", result.json["record"]["funding_tier"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            cached = self.client.post("/api/generate-thesis", json={"startup_id": 1})
        self.assertTrue(cached.json["cached"])
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("cloud_ai.requests.post")
    def test_provider_limit_does_not_create_a_fake_note(self, post):
        post.return_value = Mock(status_code=429)
        response = self.client.post("/api/generate-thesis", json={"startup_id": 1})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)
        self.assertEqual(self.client.get("/api/ai-summaries").json["records"], [])

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("cloud_ai.requests.post")
    def test_provider_error_does_not_leak_credentials(self, post):
        response = Mock(status_code=401)
        post.return_value = response
        response.raise_for_status.side_effect = requests.HTTPError("secret must stay private", response=response)
        result = self.client.post("/api/generate-thesis", json={"startup_id": 1})
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("test-key", result.get_data(as_text=True))
        self.assertNotIn("secret", result.get_data(as_text=True))

    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    def test_missing_key_is_clear_and_does_not_break_the_dashboard(self):
        self.assertEqual(self.client.post("/api/generate-thesis", json={"startup_id": 1}).status_code, 503)
        self.assertEqual(self.client.get("/api/stats").status_code, 200)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("cloud_ai.requests.post")
    def test_generation_limit_stops_new_provider_calls_but_keeps_cache_available(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"choices": [{"message": {"content": "A research hypothesis. A risk to review."}}]}
        for company_id in (1, 2, 3, 5, 6):
            self.assertEqual(self.client.post("/api/generate-thesis", json={"startup_id": company_id}).status_code, 200)
        limited = self.client.post("/api/generate-thesis", json={"startup_id": 7})
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(post.call_count, 5)
        self.assertTrue(self.client.post("/api/generate-thesis", json={"startup_id": 1}).json["cached"])
        self.assertEqual(post.call_count, 5)

    def test_founding_year_filter_excludes_unknown_years(self):
        data = self.client.get("/api/companies?year_from=1900").json
        self.assertEqual(data["total"], 7)
        self.assertNotIn(4, [row["id"] for row in data["records"]])


if __name__ == "__main__":
    unittest.main()
