# IT Asset Manager

A secure Flask application for managing IT assets. Users can register, log in, view available assets, and submit asset requests. Administrators can approve or deny requests, manage the asset catalogue, and unassign assets when required.

The project is built with Flask, SQLAlchemy, Flask-Login, Flask-WTF, Jinja templates, Bootstrap 5, SQLite for local development, Gunicorn, Docker, and GitHub Actions.

## Features

- User registration and login with role-based access for `admin` and `user` accounts.
- Admin approval workflow for asset requests.
- Asset create, read, update, delete, assignment, and unassignment flows.
- Server-side form validation for users, assets, request reasons, serial numbers, and asset statuses.
- Flash messages for clear user feedback.
- Bootstrap dashboard with asset status and assignment information.
- CI checks for tests, linting, dependency auditing, and Python security scanning.
- Deployment artefacts for Gunicorn, Docker, and Render.

## Secure Local Setup

1. Clone the repository and enter the project directory.

```bash
git clone https://github.com/yourusername/it-asset-manager.git
cd it-asset-manager
```

2. Create and activate a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
```

On Windows, activate with:

```powershell
venv\Scripts\activate
```

3. Install dependencies.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. Configure environment variables. The app requires `SECRET_KEY`; use `.env.example` as a template for hosting platforms, but export variables in the shell for local commands.

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="sqlite:///assets.db"
export FLASK_DEBUG=0
export SESSION_COOKIE_SECURE=0
```

5. Seed the local database with demo data.

```bash
python seed.py
```

This recreates the local SQLite database and inserts local-only demonstration accounts:

- Admin: username `admin`, password `admin123`
- User: username `alice`, password `password`
- User: username `bob`, password `password`

6. Run the development server.

```bash
python app.py
```

Open `http://127.0.0.1:5000/`.

## OWASP Security Protections

- Broken Access Control: protected routes use Flask-Login, and administrator-only actions are restricted with role checks before asset management or request approval logic runs.
- Cryptographic Failures: passwords are stored using Werkzeug password hashes, and session signing uses `SECRET_KEY` from the environment instead of a hardcoded value.
- Injection: database access uses SQLAlchemy ORM queries rather than hand-built SQL strings.
- Cross-Site Request Forgery: Flask-WTF CSRF protection is enabled globally, and mutating routes such as logout, approve, deny, delete, and unassign use `POST`.
- Cross-Site Scripting: Jinja templates escape output by default, and WTForms validators reject unsupported characters in asset names, serial numbers, and asset types.
- Identification and Authentication Failures: repeated failed login attempts are throttled, and failed logins are written to the application audit log.
- Security Misconfiguration: production debug mode is disabled through `FLASK_DEBUG=0`, session cookies use `HttpOnly` and `SameSite=Lax`, secure cookies can be enabled for HTTPS hosting, security headers are applied to every response, local databases and `.env` files are ignored by Git, and production startup uses Gunicorn via `wsgi.py`.
- Security Logging and Monitoring Failures: failed logins, login throttling, and administrator asset/request actions are logged for audit evidence.

## Test Evidence

Run the automated test suite with:

```bash
pytest
```

The pytest suite uses Flask's test client and an isolated in-memory SQLite database. Current coverage includes:

- Registration, login, invalid login, and POST-only logout.
- Security headers, session cookie flags, login throttling, and audit logging.
- Redirects for protected pages when unauthenticated.
- Access control preventing regular users from admin and asset-management routes.
- Admin asset creation, editing, and deletion.
- Request submission, duplicate pending request prevention, approval, denial, unassignment, and assigned-asset delete rules.
- Validation failures for weak passwords, duplicate usernames, duplicate serial numbers, invalid asset names, invalid assignment status changes, and short request reasons.

## CI Evidence

GitHub Actions workflow: `.github/workflows/ci.yml`.

The CI pipeline runs on every push and pull request using Python 3.12. It installs dependencies and executes:

```bash
ruff check .
pytest
bandit -c pyproject.toml -r .
pip-audit --cache-dir "$RUNNER_TEMP/pip-audit-cache" --requirement requirements.txt
```

Evidence to capture for submission:

- Latest passing GitHub Actions run URL: `TODO`
- Screenshot of the passing `Tests, linting, and security checks` job: `TODO`
- Any relevant failed-run screenshot showing an issue fixed during development: `TODO`

## Deployment Evidence

Deployment-ready files are included in the repository:

- `wsgi.py` exposes the Flask app for Gunicorn.
- `Dockerfile` builds a Python 3.12 container and runs as a non-root `app` user.
- `.dockerignore` keeps local development files out of the image.
- `render.yaml` defines a Render web service using `gunicorn wsgi:app`.
- `DEPLOYMENT.md` documents environment variables, Docker commands, Render setup, and the final evidence checklist.

Run locally in production mode with:

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_DEBUG=0
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

Or build and run with Docker:

```bash
docker build -t sedo-secure-app .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e FLASK_DEBUG=0 \
  sedo-secure-app
```

Record deployment evidence here when the app is deployed:

- Deployment URL: `TODO`
- Deployment platform: `TODO`
- Deployment date: `TODO`
- Screenshot of the deployed login or home page: `TODO`
- Screenshot or log excerpt showing Gunicorn started successfully: `TODO`
- Screenshot of production environment variables with secret values hidden: `TODO`

## Entity Relationship Diagram

```text
User
- id: integer primary key
- username: unique string
- password: hashed string
- role: admin or user

Asset
- id: integer primary key
- name: string
- serial_number: unique string
- type: string
- status: available, assigned, or maintenance

Request
- id: integer primary key
- user_id: foreign key to User
- asset_id: foreign key to Asset
- status: pending, approved, denied, or revoked
- reason: text
```

## Usage Notes

- Users can register, log in, view assets, submit asset requests, and see which assets are assigned to them.
- Admins can approve or deny requests, add assets, edit assets, delete unassigned assets, view assignments, and unassign assets.
- Assets cannot be assigned to multiple users at the same time.
- Assigned assets must be unassigned before deletion.
- SQLite is suitable for local development and assignment demos. For a real multi-user production deployment, use a managed database and set `DATABASE_URL`.
