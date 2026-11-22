# Proposal

## Why

The project runs only through `uv run ... runserver`. There is no way to run the checks the same way in CI, and no production setup: `runserver` is not a production server, and with `DEBUG` off Django does not serve `/static/`, so the admin and Swagger UI would be unstyled. A reviewer cannot start the app as it would run in production.

## What Changes

- Add a multi-stage `Dockerfile` with a `test` target (dev dependencies, runs the full check suite), a `prod` target (gunicorn, non-root, no dev dependencies) and a `web` target (nginx with the collected static files and the site config baked in).
- Add `docker-compose.prod.yml` running `app` (gunicorn) and `web` (nginx). nginx terminates TLS, redirects HTTP to HTTPS, serves `/static/` and proxies the rest to `app`. Only nginx is published to the host.
- Add an entrypoint that applies migrations and then starts gunicorn. It never loads demo fixtures.
- Add `.env.prod.example` and `nginx.conf`. `SECRET_KEY` and `ALLOWED_HOSTS` have no defaults in the prod compose file. TLS certificates are mounted from `certs/` (not committed).
- Add `.dockerignore` so `.env`, `*.sqlite3`, `.venv`, `.git` and certificates never enter an image.
- Add `gunicorn` as a runtime dependency.
- README: a Docker section for the test and prod commands. The local setup (`uv run --env-file .env ... runserver`, plain HTTP, no nginx, no certificates) is unchanged.

Out of scope: a CI workflow file, certificate issuance or renewal, a PostgreSQL or Redis service, a local Docker dev mode, and any change to `settings.py`.

## Capabilities

### New Capabilities
- `deployment`: how the app is built and run in containers: the containerised check suite and the production stack (app server, TLS front end, static files, data persistence, startup behaviour).

### Modified Capabilities

None. The `web-security` requirements (production mode, environment configuration) are used as they are.

## Impact

- New files at the repo root: `Dockerfile`, `docker-compose.prod.yml`, `.dockerignore`, `.env.prod.example`, `docker/nginx.conf`, `docker/entrypoint.sh`.
- `pyproject.toml` and `uv.lock`: add `gunicorn`.
- `README.md`: new Docker section.
- No application code, models or API change.
