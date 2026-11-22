# Targets: test (run the checks), prod (gunicorn app), web (nginx + static files).
# syntax=docker/dockerfile:1

FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app


# --- test: dev dependencies, baked-in test environment ------------------------
FROM base AS test
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
ENV DEBUG=1 \
    SECRET_KEY=django-insecure-container-test-key \
    SQLITE_PATH=/tmp/db.sqlite3 \
    SQLITE_TEST_PATH=/tmp/test_db.sqlite3
CMD ["sh", "docker/check.sh"]


# --- prod dependencies and collected static files -----------------------------
FROM base AS prod-deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM prod-deps AS collect
COPY . .
RUN SECRET_KEY=build-only-not-a-secret python manage.py collectstatic --no-input


# --- prod: gunicorn, unprivileged ---------------------------------------------
FROM python:3.14-slim AS prod
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    SQLITE_PATH=/data/db.sqlite3
RUN useradd --system --uid 10001 --home-dir /app app && mkdir /data && chown app /data
WORKDIR /app
COPY --from=prod-deps /opt/venv /opt/venv
COPY --chown=root:root . .
USER app
VOLUME /data
EXPOSE 8000
ENTRYPOINT ["sh", "docker/entrypoint.sh"]


# --- web: nginx with the static files and site config -------------------------
FROM nginx:alpine AS web
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=collect /app/staticfiles /srv/static
