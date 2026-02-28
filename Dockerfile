# ---------- build stage ----------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev group)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# ---------- runtime stage ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the virtual environment and project from builder
COPY --from=builder /app /app

# Collect static files at build time using placeholder secrets
RUN DJANGO_SECRET_KEY=build-placeholder \
    DATABASE_URL=sqlite:///tmp/placeholder.db \
    DJANGO_ALLOWED_HOSTS=placeholder \
    DJANGO_ADMIN_URL=admin/ \
    ROLLBAR_ACCESS_TOKEN=placeholder \
    python manage.py collectstatic --noinput

RUN chmod +x /app/run.sh

EXPOSE 8000

CMD ["/app/run.sh"]
