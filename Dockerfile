FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /srv/app/data/storage /srv/app/data/reports

# Default command runs the Telegram bot; overridden per-service in docker-compose.yml.
CMD ["python", "-m", "app.main"]
