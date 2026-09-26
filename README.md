# Documentor

Documentor is a Telegram bot for reviewing student papers in DOCX format. It checks formatting and structure, analyzes language, academic style, and content, and produces a PDF report with actionable recommendations.

The project is designed for universities in Kazakhstan. It includes provisional presets for coursework, graduation theses, essays, and internship reports at Makhambet Utemisov West Kazakhstan University. The interface and reports support Russian, Kazakh, and English.

## Features

- Checks fonts, text size, margins, line spacing, indentation, and headings.
- Detects document sections and performs basic checks of references and citations.
- Reviews grammar, academic style, and reasoning through a configured AI service.
- Provides a score out of 100, category scores, and explanations of deductions.
- Generates PDF reports with issue locations, short excerpts, and recommendations.
- Keeps a check history, supports downloading reports again, and allows users to delete completed checks.
- Processes documents in the background and retries delivery after temporary Telegram failures.

## Usage

Open the bot, send `/start`, and select a language and document type. Upload a DOCX file; you can include the research topic in its caption. Once processing is complete, the bot displays the result and offers a PDF report.

## Scoring

Each category has a weight defined in the selected rules preset. Repeated observations of the same issue do not multiply the penalty. Category scores cannot fall below zero.

The overall maximum is always **100 points**. A complete review combines five categories: formatting, structure, language, style, and content. If some AI requests fail, successful assessments are retained and the proportion of text reviewed is displayed for each AI category. The overall score is normalized to 100 using the available categories and clearly marked as provisional. Unreviewed categories are not assigned fabricated scores.

This is a diagnostic score, not a grade awarded by a supervisor or examination committee. AI assessments can be incorrect. The service does not detect plagiarism, verify the authenticity of sources, or assess an oral defense.

Presets must be checked against the current guidelines of the relevant department. Unverified minimum word and source counts are treated as recommendations without score deductions.

## Run with Docker

Docker with Compose support is required.

1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN` and the AI service settings: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, and optionally `LLM_BASE_URL`.
3. Start the application:

```bash
docker compose up --build -d
```

Compose starts PostgreSQL, Redis, database migrations, the bot, and the document worker. Persistent data is stored in separate volumes. PostgreSQL and Redis ports are not exposed to the host.

```bash
docker compose ps
docker compose logs --tail 50 bot worker
docker compose stop
```

To run without an external AI service, set `LLM_PROVIDER=mock`. Formatting and structure checks remain available; language, style, and content are marked as unreviewed.

## Local development

Python 3.12 and Redis are required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.database.bootstrap
python -m app.main
```

Start the worker in another terminal with the same environment:

```bash
arq app.worker.WorkerSettings
```

Local development uses SQLite by default. Database schema changes are managed by Alembic.

## Configuration

Formatting rules and category weights are stored in `rules/presets`. The active AI prompt is `prompts/review.txt`. Restart the bot and worker after changing configuration. Previously saved results are not recalculated.

`MAX_AI_TOKENS_PER_CHECK` limits the AI review budget, and `LLM_ANALYSIS_TIMEOUT_SECONDS` limits the duration of the AI stage. File size limits, usage quotas, and retention periods are configured in `.env`.

PDF generation requires a font with Russian and Kazakh character support. The Docker image includes DejaVu Sans. In a custom environment, set `PDF_FONT_PATH` and `PDF_FONT_PATH_BOLD` if needed.

## Architecture

The Telegram bot receives a file and saves a job in SQL. Redis passes the job ID to the worker. The worker parses the DOCX file, applies deterministic rules, performs AI analysis, and saves the result. Report generation and delivery are separate from analysis, so delivery retries do not trigger additional AI requests.

Rules, scoring, AI response validation, and report presentation are organized into separate modules. Each check stores a snapshot of its rules, the scoring version, and analysis coverage. Telegram and PDF reports use a shared presentation layer.

## Testing

```bash
ruff check app tests
pytest -q
```

Tests do not require working Telegram or AI credentials. PostgreSQL and Redis integration tests run against isolated services configured in `docker-compose.test.yml`; see the [architecture documentation](docs/ARCHITECTURE.md) for details.

Preview a PDF without Telegram or AI:

```bash
python -m app.reports.preview demo/bad_example_makhambet.docx output/pdf/example.pdf
```

## Data handling

The source DOCX file is deleted after the analysis result is saved. Text excerpts are sent to the configured external AI service; institutions should consider this when choosing a provider and defining usage policies. Reports may contain short quotations. Results and PDFs have separate configurable retention periods. Secrets in `.env` are excluded from the repository and Docker image.

## Documentation

The following supporting documents are currently written in Russian:

- [Architecture and operations](docs/ARCHITECTURE.md)
- [Review of WKU requirements](docs/WKU_REVIEW.md)
- [Project defense speech](docs/DEFENSE_SPEECH.md)
- [Demonstration guide](DEFENSE.md)
