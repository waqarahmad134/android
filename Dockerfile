# Multi-exchange trading bot — slim, production-ish image for 24/7 running.
FROM python:3.11-slim

# Don't write .pyc, flush logs immediately (so `docker logs` is live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code and config.
COPY src/ ./src/
COPY config/ ./config/

# Run as a non-root user.
RUN useradd --create-home --uid 10001 trader \
    && mkdir -p /app/logs \
    && chown -R trader:trader /app
USER trader

# Defaults to the trading loop (paper mode unless config says otherwise).
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["run"]
