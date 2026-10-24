"""Application setup, database configuration, and shared HTTP behavior."""
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from analytics import register_analytics
from cloud_ai import register_cloud_ai

ROOT = Path(__file__).resolve().parent


def create_app(config=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(MAX_CONTENT_LENGTH=4096)
    app.config.update(config or {})
    database_url = app.config.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        database_url = URL.create(
            "mysql+pymysql", username=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""), host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")), database=os.getenv("DB_NAME", "vc_analytics_db"),
        )
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
    app.extensions["database"] = engine
    if engine.dialect.name == "sqlite" and engine.url.database not in (None, ":memory:"):
        if app.config.get("AUTO_PREPARE_DB", True):
            from prepare_cloud_db import prepare
            prepare(engine.url.database)

    @app.get("/")
    def landing():
        return render_template("landing.html", page="landing")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html", page="dashboard")

    @app.get("/methodology")
    def methodology():
        return render_template("methodology.html", page="methodology")

    @app.get("/api/health")
    def health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM startup_investments LIMIT 1"))
            return jsonify(status="ok", database="connected", database_type=engine.dialect.name,
                           ai_configured=bool(os.getenv("GROQ_API_KEY", "").strip()))
        except SQLAlchemyError:
            return jsonify(status="degraded", error="Data service is temporarily unavailable."), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        app.logger.error("Database request failed (%s)", type(error).__name__)
        return jsonify(error="Data service is temporarily unavailable. Please try again."), 503

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    register_analytics(app, engine)
    register_cloud_ai(app, engine)
    return app
