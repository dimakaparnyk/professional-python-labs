FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md MANIFEST.in ./
COPY src ./src
COPY migrations ./migrations
COPY data ./data
COPY config.yaml ./
COPY requirements.lock ./
RUN pip install --no-cache-dir build && python -m build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1     DATABASE_URL=sqlite:////data/inventory.db APP_ENV=production LOG_LEVEL=INFO
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -c /tmp/requirements.lock /tmp/*.whl     && useradd --create-home --uid 10001 appuser     && mkdir -p /data && chown appuser:appuser /data
USER appuser
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3     CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "inventory_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
