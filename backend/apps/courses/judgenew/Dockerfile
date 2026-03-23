FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    gcc \
    g++ \
    bash \
    coreutils \
    ca-certificates \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Alohida foydalanuvchi — root emas
RUN useradd --create-home --shell /usr/sbin/nologin --uid 1000 runner

USER runner
WORKDIR /work
