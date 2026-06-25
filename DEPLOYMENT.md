# Deployment Guide

This project can be deployed as a standard Flask application behind Gunicorn, either directly on a Python hosting platform or inside Docker.

## Required Environment Variables

Set these values in the hosting platform or container environment:

- `SECRET_KEY`: required. Use a long, random value generated for the deployment.
- `DATABASE_URL`: optional. Defaults to `sqlite:///assets.db` for local/demo use.
- `FLASK_DEBUG`: set to `0` in production.
- `PORT`: optional. Used by the Docker image and some platforms. Defaults to `8000`.

Never commit real production secrets. Use `.env.example` only as a template.

## Local Production Run

Install dependencies and start the app with Gunicorn:

```bash
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_DEBUG=0
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

Open `http://127.0.0.1:8000`.

## Docker Deployment

Build and run the container:

```bash
docker build -t sedo-secure-app .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e FLASK_DEBUG=0 \
  sedo-secure-app
```

For persistent SQLite data, mount the `instance` directory:

```bash
mkdir -p instance
docker run --rm -p 8000:8000 \
  -v "$PWD/instance:/app/instance" \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e DATABASE_URL=sqlite:///assets.db \
  -e FLASK_DEBUG=0 \
  sedo-secure-app
```

SQLite is suitable for the assignment demo and local deployments. For a real multi-user production service, use a managed database and set `DATABASE_URL` accordingly.

## Render Deployment

The repository includes `render.yaml` for a simple Render web service.

1. Push the repository to GitHub.
2. In Render, create a new Blueprint or web service from the repository.
3. Set `SECRET_KEY` as a secret environment variable.
4. Confirm `FLASK_DEBUG=0`.
5. Deploy and open the generated URL.

The start command is:

```bash
gunicorn wsgi:app
```

## Deployment Evidence

Capture these items for the assignment evidence pack:

- Deployed application URL.
- Screenshot of the home or login page served from the deployed URL.
- Screenshot of the hosting platform showing the latest successful deployment.
- Screenshot or log excerpt showing Gunicorn started successfully.
- Screenshot of configured environment variables with secret values hidden.
- Link or screenshot for the latest passing CI run.

Record the final values below when deployment is complete:

- Deployment URL: `TODO`
- Deployment platform: `TODO`
- Deployment date: `TODO`
- CI run URL: `TODO`
