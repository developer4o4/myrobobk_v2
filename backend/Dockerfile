# ─── Stage 1: dependencies ───────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /app/requirements/
RUN pip install --upgrade pip --no-cache-dir \
 && pip install --no-cache-dir -r requirements/base.txt

# ─── Stage 2: production image ───────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Docker CLI (judge uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-cli \
    ca-certificates \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Faqat o'rnatilgan paketlarni olamiz (source emas)
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Ilova kodini ko'chiramiz
COPY . /app

# Root bo'lmagan foydalanuvchi
RUN useradd --create-home --shell /bin/bash --uid 1001 appuser \
 && mkdir -p /app/staticfiles /app/media \
 && chown -R appuser:appuser /app

USER appuser

EXPOSE 7712

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:7712", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "60", \
     "--keep-alive", "5", \
     "--log-level", "warning", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
