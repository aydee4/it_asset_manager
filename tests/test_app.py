import logging

from conftest import create_request, login, logout
from extensions import db
from models import Asset, Request, User


def test_security_headers_and_session_cookie_flags(client, create_user):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]

    create_user(username="alice")
    response = login(client, username="alice", follow_redirects=False)
    session_cookie = response.headers["Set-Cookie"]

    assert "HttpOnly" in session_cookie
    assert "SameSite=Lax" in session_cookie


def test_login_rate_limit_blocks_repeated_failures(client, create_user):
    create_user(username="locked")
    client.application.config["LOGIN_RATE_LIMIT_ATTEMPTS"] = 2
    client.application.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = 300

    for _ in range(2):
        response = login(client, username="locked", password="wrong-password")
        assert b"Invalid username or password" in response.data

    response = login(client, username="locked", password="Password123!")

    assert response.status_code == 429
    assert b"Too many failed login attempts" in response.data


def test_security_audit_events_are_logged(client, create_user, create_asset, caplog):
    admin = create_user(username="admin", role="admin")
    user = create_user(username="requester")
    asset = create_asset()
    asset_request = create_request(user, asset)

    caplog.set_level(logging.INFO)
    login(client, username="admin", password="wrong-password")
    login(client, username=admin.username)
    client.post(f"/admin/approve/{asset_request.id}", follow_redirects=True)

    messages = [record.getMessage() for record in caplog.records]
    assert any("login_failed username=admin" in message for message in messages)
    assert any(
        f"admin_approved_request admin=admin request_id={asset_request.id}" in message
        for message in messages
    )


def test_registration_login_invalid_login_and_logout(client):
    response = client.post(
        "/register",
        data={
            "username": "alice",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    user = User.query.filter_by(username="alice").one()
    assert user.role == "user"
    assert user.password != "Password123!"

    response = login(client, username="alice", password="Password123!")
    assert b"Welcome, alice!" in response.data

    response = logout(client)
    assert b"Logged out successfully" in response.data

    response = login(client, username="alice", password="wrong-password")
    assert b"Invalid username or password" in response.data


def test_protected_pages_require_login(client):
    protected_urls = [
        "/dashboard",
        "/request_asset",
        "/admin",
        "/assets",
    ]

    for url in protected_urls:
        response = client.get(url)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_and_asset_management_routes(
    client,
    create_user,
    create_asset,
):
    user = create_user(username="bob")
    asset = create_asset()
    asset_request = create_request(user, asset)

    login(client, username="bob")

    response = client.get("/admin", follow_redirects=True)
    assert b"Access denied: admin only" in response.data

    response = client.post(
        f"/admin/approve/{asset_request.id}",
        follow_redirects=True,
    )
    assert b"Access denied" in response.data
    assert db.session.get(Request, asset_request.id).status == "pending"
    assert db.session.get(Asset, asset.id).status == "available"

    response = client.get("/assets", follow_redirects=True)
    assert b"Admin access required" in response.data

    response = client.post(
        "/assets/add",
        data={"name": "Tablet", "serial": "TAB-001", "type": "Tablet"},
        follow_redirects=True,
    )
    assert b"Admin access required" in response.data
    assert Asset.query.filter_by(serial_number="TAB-001").first() is None

    response = client.post(
        f"/assets/delete/{asset.id}",
        follow_redirects=True,
    )
    assert b"Admin access required" in response.data
    assert db.session.get(Asset, asset.id) is not None


def test_admin_can_create_edit_and_delete_assets(client, create_user):
    create_user(username="admin", role="admin")
    login(client, username="admin")

    response = client.post(
        "/assets/add",
        data={"name": "Dev Laptop", "serial": "DEV-001", "type": "Laptop"},
        follow_redirects=True,
    )
    assert b"Asset added" in response.data

    asset = Asset.query.filter_by(serial_number="DEV-001").one()
    assert asset.name == "Dev Laptop"
    assert asset.status == "available"

    response = client.post(
        f"/assets/edit/{asset.id}",
        data={
            "name": "Dev Laptop Pro",
            "serial": "DEV-001A",
            "type": "Laptop",
            "status": "maintenance",
        },
        follow_redirects=True,
    )
    assert b"Asset updated" in response.data

    asset = db.session.get(Asset, asset.id)
    assert asset.name == "Dev Laptop Pro"
    assert asset.serial_number == "DEV-001A"
    assert asset.status == "maintenance"

    response = client.post(
        f"/assets/delete/{asset.id}",
        follow_redirects=True,
    )
    assert b"Asset deleted" in response.data
    assert db.session.get(Asset, asset.id) is None


def test_request_workflow_approval_denial_unassignment_and_delete_rules(
    client,
    create_user,
    create_asset,
):
    user = create_user(username="carol")
    admin = create_user(username="admin", role="admin")
    laptop = create_asset(name="Laptop", serial_number="LAP-001")
    phone = create_asset(name="Phone", serial_number="PHN-001", type="Phone")

    login(client, username=user.username)
    response = client.post(
        "/request_asset",
        data={
            "asset_id": laptop.id,
            "reason": "Needed for the secure development assignment",
        },
        follow_redirects=True,
    )
    assert b"Asset request submitted" in response.data

    request = Request.query.filter_by(user_id=user.id, asset_id=laptop.id).one()
    assert request.status == "pending"

    response = client.post(
        "/request_asset",
        data={
            "asset_id": laptop.id,
            "reason": "Needed for the secure development assignment",
        },
        follow_redirects=True,
    )
    assert b"You already have a pending request" in response.data
    assert Request.query.filter_by(user_id=user.id, asset_id=laptop.id).count() == 1

    logout(client)
    login(client, username=admin.username)

    response = client.post(f"/admin/approve/{request.id}", follow_redirects=True)
    assert b"Request approved and asset assigned" in response.data
    assert db.session.get(Request, request.id).status == "approved"
    assert db.session.get(Asset, laptop.id).status == "assigned"

    response = client.post(f"/assets/delete/{laptop.id}", follow_redirects=True)
    assert b"Unassign it first to delete" in response.data
    assert db.session.get(Asset, laptop.id) is not None

    response = client.post(f"/assets/unassign/{laptop.id}", follow_redirects=True)
    assert b"has been unassigned and is now available" in response.data
    assert db.session.get(Request, request.id).status == "revoked"
    assert db.session.get(Asset, laptop.id).status == "available"

    response = client.post(f"/assets/delete/{laptop.id}", follow_redirects=True)
    assert b"Asset deleted" in response.data
    assert db.session.get(Asset, laptop.id) is None

    denied_request = create_request(user, phone)
    response = client.post(f"/admin/deny/{denied_request.id}", follow_redirects=True)
    assert b"Request denied" in response.data
    assert db.session.get(Request, denied_request.id).status == "denied"

    response = client.post(f"/admin/approve/{denied_request.id}", follow_redirects=True)
    assert b"Only pending requests can be approved" in response.data
    assert db.session.get(Request, denied_request.id).status == "denied"
    assert db.session.get(Asset, phone.id).status == "available"


def test_validation_failures_keep_bad_data_out(client, create_user, create_asset):
    response = client.post(
        "/register",
        data={
            "username": "weakuser",
            "password": "password",
            "confirm_password": "password",
        },
    )
    assert b"Password must be between 10 and 128 characters" in response.data
    assert User.query.filter_by(username="weakuser").first() is None

    create_user(username="existing")
    response = client.post(
        "/register",
        data={
            "username": "existing",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    assert b"Username already exists" in response.data

    create_user(username="admin", role="admin")
    login(client, username="admin")

    existing_asset = create_asset(serial_number="DUP-001")
    response = client.post(
        "/assets/add",
        data={"name": "Other Laptop", "serial": "DUP-001", "type": "Laptop"},
    )
    assert b"Asset with that serial number already exists" in response.data
    assert Asset.query.filter_by(serial_number="DUP-001").count() == 1

    response = client.post(
        "/assets/add",
        data={"name": "<script>", "serial": "BAD-001", "type": "Laptop"},
    )
    assert b"Name contains unsupported characters" in response.data
    assert Asset.query.filter_by(serial_number="BAD-001").first() is None

    response = client.post(
        f"/assets/edit/{existing_asset.id}",
        data={
            "name": "Assigned Laptop",
            "serial": "DUP-001",
            "type": "Laptop",
            "status": "assigned",
        },
    )
    assert b"Assign assets by approving a pending request" in response.data
    assert db.session.get(Asset, existing_asset.id).status == "available"

    logout(client)
    regular_user = create_user(username="requester")
    login(client, username=regular_user.username)

    response = client.post(
        "/request_asset",
        data={"asset_id": existing_asset.id, "reason": "Too short"},
    )
    assert b"Reason must be between 10 and 500 characters" in response.data
    assert Request.query.filter_by(user_id=regular_user.id).first() is None
