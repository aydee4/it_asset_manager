import os
import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import app as flask_app, login_attempts  # noqa: E402
from extensions import db  # noqa: E402
from models import Asset, Request, User  # noqa: E402


@pytest.fixture()
def app():
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with flask_app.app_context():
        login_attempts.clear()
        db.drop_all()
        db.create_all()
        yield flask_app
        login_attempts.clear()
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def create_user(app):
    def _create_user(username="user", password="Password123!", role="user"):
        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        return user

    return _create_user


@pytest.fixture()
def create_asset(app):
    def _create_asset(
        name="Laptop",
        serial_number="SERIAL-001",
        type="Laptop",
        status="available",
    ):
        asset = Asset(
            name=name,
            serial_number=serial_number,
            type=type,
            status=status,
        )
        db.session.add(asset)
        db.session.commit()
        return asset

    return _create_asset


def login(client, username="user", password="Password123!", follow_redirects=True):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=follow_redirects,
    )


def logout(client, follow_redirects=True):
    return client.post("/logout", follow_redirects=follow_redirects)


def create_request(user, asset, reason="Needed for secure development work"):
    asset_request = Request(
        user_id=user.id,
        asset_id=asset.id,
        reason=reason,
        status="pending",
    )
    db.session.add(asset_request)
    db.session.commit()
    return asset_request
