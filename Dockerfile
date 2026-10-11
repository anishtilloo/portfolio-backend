# API image: FastAPI + Alembic, run by uvicorn.
#   docker build -t portfolio-api backend
#   docker run -p 8000:8000 -e DATABASE_URL=... -e SECRET_KEY=... portfolio-api

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app/backend

# Dependencies first so they stay cached until pyproject/uv.lock change.
# uv.lock is optional: --frozen when it is there, a fresh resolve when not.
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev --no-install-project; \
    else uv sync --no-dev --no-install-project; fi

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=4)"

# Apply migrations, then start. Most hosts set PORT; default is 8000.
CMD alembic upgrade head && \
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} \
         --proxy-headers --forwarded-allow-ips='*'
