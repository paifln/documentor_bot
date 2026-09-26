FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY rules ./rules
COPY prompts ./prompts
COPY alembic.ini .
RUN useradd --create-home --uid 10001 documentor && mkdir -p data/storage data/reports && chown -R documentor:documentor data
USER documentor
CMD ["python", "-m", "app.main"]
