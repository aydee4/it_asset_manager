import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///assets.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(
        os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")
    )


def validate_config(app):
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY environment variable must be set.")
