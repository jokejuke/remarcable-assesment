# Tasks

## 1. Dependencies and image hygiene

- [x] 1.1 Add `gunicorn` as a runtime dependency (`uv add gunicorn`); verify `uv.lock` updates and `uv run python -c "import gunicorn"` works
- [x] 1.2 Add `.dockerignore` (env files except examples, `*.sqlite3`, `.venv`, `.git`, `openspec/`, caches, `certs/`) and a `.gitignore` entry for `.env.prod` and `certs/`; verify `git status` ignores them and a built image has none of them

## 2. Test target

- [x] 2.1 Write the `Dockerfile` `base` and `test` stages with the baked-in test environment and writable database paths; verify `docker build --target test .` succeeds
- [x] 2.2 Add the check script (tests, `makemigrations --check`, `spectacular --validate --fail-on-warn`, `ruff check`) as the default command; verify `docker run --rm <image>` exits 0 on the clean tree with no `-e` or `.env`
- [x] 2.3 Verify failure propagation: temporarily break a test, run the container, confirm a non-zero exit, then revert

## 3. Production app image

- [x] 3.1 Add the `prod` stage (no dev deps, non-root user, `/data` owned by that user) and `docker/entrypoint.sh` (`migrate --no-input`, then `exec gunicorn` with one worker and several threads); verify the container starts on an empty volume and creates the schema
- [x] 3.2 Verify `docker run` with no `SECRET_KEY` fails naming the variable, and that no demo user exists after a fresh start
- [x] 3.3 Verify the image runs as non-root and contains no `.env`, `*.sqlite3` or `.git` (`docker run --rm --entrypoint id <image>`, `docker run --rm --entrypoint find ...`)

## 4. nginx front end and compose stack

- [x] 4.1 Add `docker/nginx.conf` (80 to 443 redirect, TLS from `/etc/nginx/certs`, proxy to `app:8000`, forwarded headers set from `$scheme`, `server_tokens off`, body size limit, gzip, `/static/`) and the `web` stage (collectstatic output + config); verify `nginx -t` passes inside the built image
- [x] 4.2 Add `docker-compose.prod.yml` (`app` with data volume, healthcheck and required variables; `web` publishing 80/443 with certs mounted read-only and `depends_on` healthy) and `.env.prod.example`; verify `docker compose config` fails without `SECRET_KEY` or `ALLOWED_HOSTS`
- [x] 4.3 Run the stack with a self-signed certificate and verify: HTTP redirects to HTTPS, `/` returns 200, `/static/admin/css/base.css` returns 200, an unknown URL gives the plain 404, the app port is not reachable from the host, and a spoofed `X-Forwarded-Proto` over HTTP is still redirected
- [x] 4.4 Verify login works over HTTPS (Secure session cookie, no redirect loop), then `docker compose down` and `up` and confirm an account created earlier is still there

## 5. Documentation

- [x] 5.1 Add a Docker section to `README.md`: the test command, the prod setup (copy `.env.prod.example`, put certs in `certs/`, a self-signed example command, `docker compose -f docker-compose.prod.yml up -d --build`), the one-worker and SQLite notes, and the "never load `demo_users` in production" warning; verify every documented command runs as written
- [x] 5.2 Confirm the existing local setup section is unchanged and still works (`uv run --env-file .env python manage.py test` passes)
