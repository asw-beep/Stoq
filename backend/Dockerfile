# Backend image. Uses uv for fast, reproducible installs.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # FinBERT model files are cached here; mount a named volume at this path
    # so the ~500 MB download survives container rebuilds.
    HF_HOME=/hf_cache

# uv: copied from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

# App source.
COPY . .

# Run as an unprivileged user — never as root (W-7 / HIGH-005).
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then start the API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
