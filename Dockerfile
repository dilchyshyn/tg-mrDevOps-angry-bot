# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY bot ./bot
COPY config ./config
COPY quotes ./quotes
RUN pip install .

# /data: точка монтування volume зі станом. Новий named volume переймає власника з образу
RUN useradd --create-home --uid 10001 mrdevops \
    && mkdir /data \
    && chown -R mrdevops /app /data
USER mrdevops

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,time,sys; p='/tmp/mrdevops.heartbeat'; sys.exit(0 if os.path.exists(p) and time.time()-os.path.getmtime(p) < 120 else 1)"

CMD ["python", "-m", "bot.main"]
