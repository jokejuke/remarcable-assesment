# Design

## Context

The app reads all deployment values from the environment (`config/settings.py`). With `DEBUG` off it forces HTTPS, secure cookies and HSTS, and it trusts `X-Forwarded-Proto` only when `TRUST_X_FORWARDED_PROTO=1`. `STATIC_ROOT` is `staticfiles/`. The database is a SQLite file at `SQLITE_PATH`; the cache is per-process (`LocMemCache`), so one worker only. `test_settings.py` starts subprocesses with a cleaned environment, so it does not depend on the ambient `DEBUG`. See proposal.md for motivation and scope.

## Goals / Non-Goals

**Goals:**
- One command to run the same checks as the README's development workflow, inside a container.
- A production stack that works end to end: HTTPS, static files, persistent data, no debug.
- No change to `settings.py` or application code.

**Non-Goals:**
- CI workflow files, certificate issuance or renewal, horizontal scaling, PostgreSQL or Redis.
- A Docker-based local dev mode. Local development stays `uv run ... runserver` over HTTP.

## Decisions

**D1. One multi-stage Dockerfile, three runtime targets.** A shared `base` (python:3.14-slim, uv, dependencies from `uv.lock`) feeds `test`, `prod` and `web`. This keeps one definition of the dependency set. Alternative: separate Dockerfiles per purpose. Rejected: they drift apart.

**D2. `test` target** installs with the dev group (`ruff`, `vulture`), copies the source and sets `DEBUG=1`, a throwaway `SECRET_KEY` and `SQLITE_PATH`/`SQLITE_TEST_PATH` under a writable temp directory. Its default command runs a script that executes, in order, `manage.py test`, `makemigrations --check`, `spectacular --validate --fail-on-warn` and `ruff check`, and fails if any of them fails (it runs all four and reports, so one run shows every failure). The environment is baked in so the caller supplies nothing. The test database is a file, so the checkout concurrency test still uses real SQLite locks.

**D3. `prod` target** installs with `--no-dev`, adds `gunicorn`, runs as an unprivileged user, and starts through `docker/entrypoint.sh`: `migrate --no-input`, then `exec gunicorn config.wsgi --workers 1 --threads 8`. One worker because of the per-process cache; threads give concurrency. SQLite lives at `/data/db.sqlite3` on a named volume owned by the app user. Migrations at start (not at build) because the database is on the volume.

**D4. Static files are baked into the nginx image (`web` target).** `collectstatic` runs in a build stage; the `web` target (nginx:alpine) copies the result and `nginx.conf`. Alternative: a shared named volume filled by the app container. Rejected: a named volume keeps its first contents, so static files go stale after an image update. Baking them in ties static files to the image version, needs no `STATIC_ROOT` volume and no WhiteNoise.

**D5. nginx terminates TLS.** Listens on 80 (redirect to HTTPS) and 443 (certs mounted read-only from `./certs`, `fullchain.pem` and `privkey.pem`). It proxies to `app:8000` and sets `Host`, `X-Forwarded-For` and `X-Forwarded-Proto $scheme`, which overwrites anything the client sent. `app` has no published port, so the proxy is the only way in. The prod env sets `TRUST_X_FORWARDED_PROTO=1`. HSTS stays in Django to avoid sending the header twice. Also `server_tokens off`, `client_max_body_size 1m`, and gzip for text types.

**D6. Healthcheck for `app`** uses a one-line Python request to `/accounts/login/` (anonymous, no redirect) with `Host` set to the first `ALLOWED_HOSTS` entry and `X-Forwarded-Proto: https`, so it passes the host check and the HTTPS redirect. `web` waits with `depends_on: condition: service_healthy`. No new route is added.

**D7. Required configuration.** The compose file uses `${SECRET_KEY:?...}` and `${ALLOWED_HOSTS:?...}` so a missing value stops startup with a clear message. `CSRF_TRUSTED_ORIGINS` is required in practice behind TLS and is listed in `.env.prod.example`. `.env.prod.example` holds placeholders only; the real `.env.prod` is git-ignored.

**D8. `.dockerignore`** excludes `.env*` (except examples), `*.sqlite3`, `.venv`, `.git`, `openspec/`, caches and `certs/`.

## Risks / Trade-offs

- [Gunicorn with one worker limits throughput] → Matches the documented single-process limitation; threads cover I/O waits. Scaling out needs a shared cache and PostgreSQL first.
- [SQLite on a Docker volume] → Single container only, never two writers; documented. WAL is not enabled here.
- [No certificates in the repo, so the stack does not start without them] → README documents the files expected in `certs/` and a self-signed command for trial runs.
- [Self-signed certificates and HSTS in browsers] → HSTS is one year in prod mode; README warns against trialling on a real domain with throwaway certs.
- [Healthcheck depends on `/accounts/login/` staying anonymous and non-redirecting] → The login page is a core route; the check would visibly fail if it changed.
