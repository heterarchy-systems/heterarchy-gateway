FROM ghcr.io/astral-sh/uv:0.12.3@sha256:2d890623d310b57771ce840f0da5eed5fc6d657da05ffaa45d82797b53fa3abc AS uv

FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251 AS python-base
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

FROM python-base AS python-build
COPY pyproject.toml uv.lock .python-version ./
RUN uv python install 3.14.7t \
    && uv sync --locked --no-dev --python 3.14.7t

FROM python-base AS runtime
COPY --from=python-build /opt/python /opt/python
COPY --from=python-build /app/.venv /app/.venv
COPY pyproject.toml uv.lock .python-version ./
COPY app app
ENV UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never
USER 10001:10001
RUN uv run --locked --no-sync --python 3.14.7t python -c "import sys; assert sys.version_info[:3] == (3, 14, 7) and not sys._is_gil_enabled()"
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD uv run --locked --no-sync --python 3.14.7t python -c "import httpx; httpx.get('http://127.0.0.1:8799/healthz', timeout=2, trust_env=False).raise_for_status()"
CMD ["sh", "-c", "uv run --locked --no-sync --python 3.14.7t python -c 'import sys; assert sys.version_info[:3] == (3, 14, 7) and not sys._is_gil_enabled()' && exec uv run --locked --no-sync --python 3.14.7t uvicorn app.bootstrap:create_app --factory --host 127.0.0.1 --port 8799 --loop asyncio --http h11 --workers 1 --limit-concurrency 100 --timeout-graceful-shutdown 10"]
