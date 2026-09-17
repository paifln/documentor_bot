# AI CourseWork Checker — Documentor

## 0. Готово к защите — с чего начать

- **`DEFENSE.md`** — шпаргалка: архитектура для доски, ответы на типичные
  вопросы комиссии, пошаговый сценарий демонстрации, план Б если что-то
  зависнет во время показа. **Откройте этот файл первым.**
- **`demo/good_example_makhambet.docx`** — документ без ошибок (все поля,
  шрифт, разделы и список литературы в норме) — для показа высокого балла.
- **`demo/bad_example_makhambet.docx`** — документ с намеренными ошибками
  (неверный шрифт, неверные поля, отсутствуют «Практическая часть» и
  «Заключение», всего 3 источника) — для показа реальных найденных
  проблем на демонстрации.

Telegram-бот **Documentor** для автоматической проверки курсовых и
дипломных работ (.docx) студентов **Makhambet University** на соответствие
требованиям оформления, структуры и содержания. Интерфейс доступен на
**казахском, русском и английском** языках.

Система сочетает:
- **детерминированную проверку кодом** (поля, шрифт, интервалы, отступы,
  структура, список литературы) — там, где ответ либо верен, либо нет;
- **AI-анализ текста** (грамматика, стиль, содержание) — там, где нужно
  понимание смысла.

---

## 1. Возможности (реализовано)

- Выбор языка интерфейса при первом запуске (🇰🇿/🇷🇺/🇬🇧), смена языка в
  любой момент через «⚙️ Настройки» → «🌐 Язык». Все сообщения бота, PDF-отчёт
  и текст находок (findings) генерируются на выбранном языке.
- Единственное учебное заведение — **Makhambet University**. Экран выбора
  вуза убран за ненадобностью. Поддерживаются **4 типа работ**: курсовая,
  дипломная, отчёт по практике, реферат (см. раздел 2.1).
- Полный разбор документа **независимо от языка Word-стилей**: заголовки
  определяются по языконезависимым XML-атрибутам (`w:outlineLvl`,
  `w:styleId`), а не по отображаемому названию стиля — поэтому документы,
  где Word показывает «Тақырып 1» вместо «Heading 1», распознаются
  корректно.
- Определение структуры курсовой (Введение/Кіріспе/Introduction,
  Заключение/Қорытынды/Conclusion, Список литературы/Әдебиеттер
  тізімі/References и т.д.) — на **русском, казахском и английском**.
- Проверка списка литературы, полей, шрифта, интервалов, отступов,
  выравнивания, заголовков и их нумерации.
- AI-анализ (грамматика, стиль, содержание, смысловая структура введения)
  через абстракцию `LLMProvider` — модель явно инструктируется отвечать на
  выбранном пользователем языке.
- **PDF-отчёт с корректным отображением кириллицы и казахских букв**
  (Ә Ғ Қ Ң Ө Ұ Ү Һ І) — используется встраиваемый Unicode-шрифт (DejaVu
  Sans), а не стандартные шрифты ReportLab, которые не поддерживают
  кириллицу вообще (отсюда были «чёрные квадраты»). PDF формируется на
  языке, который выбрал пользователь.
- Chunking длинных документов, scoring с настраиваемыми весами, история
  проверок, роль ADMIN, Docker, Alembic-миграции, тесты.

## 2. Языковая архитектура

### 2.1 Поддерживаемые типы работ

В университете студенты сдают не только курсовые/дипломные, но и разные
виды отчётов, поэтому добавлено 4 типа документов — по одному YAML-пресету
на каждый (`rules/presets/makhambet_*.yaml`):

| Тип работы | Пресет | Особенности требований |
|---|---|---|
| 📚 Курсовая работа | `makhambet_coursework` | Введение / Теоретическая / Практическая часть / Заключение / Литература, ≥15 источников |
| 🎓 Дипломная работа | `makhambet_diploma` | Те же разделы, но строже: ≥30 источников, до 4 уровней заголовков, обязательный разрыв страницы перед разделом |
| 📝 Отчёт по практике | `makhambet_practice_report` | Введение / **Основная часть** (без деления на теорию/практику) / Заключение / Литература, ≥8 источников, ссылки в тексте необязательны |
| 📃 Реферат | `makhambet_essay` | Та же упрощённая структура, но ещё мягче: ≥5 источников, нумерация заголовков необязательна |

Оформление (шрифт Times New Roman 14pt, поля 30/10/20/20мм, интервал 1.5)
едино для всех четырёх типов — это общий стандарт вуза. Различаются только
**структура и объём требований**, что задаётся исключительно в YAML, без
изменения кода.

Для отчёта/реферата система распознаёт раздел «Основная часть» /
«Негізгі бөлім» / «Main body» как отдельный канонический раздел
(`main_body`) — отдельно от «Теоретическая часть» / «Практическая часть»,
которые применимы только к курсовой/дипломной.



Единый модуль `app/i18n/translations.py` — словарь `MESSAGES[key][lang]`
и функция `t(key, lang, **kwargs)`. Используется **везде**: в хендлерах
бота, в валидаторах правил (`app/rules/validators/*.py`), в AI-анализаторе,
в PDF-отчёте (`app/reports/pdf.py`). Язык пользователя хранится в
`users.language` (миграция `0002_add_user_language`) и передаётся через
всю цепочку: bot handler → очередь задач (arq job kwarg `lang`) → worker →
`AnalysisPipeline.run(..., lang=...)` → `RuleEngine`/`AIAnalyzer` →
`generate_pdf(..., lang=...)`.

RulePreset YAML использует **языконезависимые ключи** разделов
(`introduction`, `theoretical_part`, `practical_part`, `conclusion`,
`references`, `appendix`) вместо русских строк — их отображаемые названия
(«Введение» / «Кіріспе» / «Introduction») генерируются на лету через `t()`.

### Шрифт в PDF (`app/reports/fonts.py`)

ReportLab поставляется только с латинскими base-14 шрифтами — в них
физически нет кириллических глифов, поэтому русский/казахский текст
рендерился чёрными прямоугольниками. `ensure_unicode_font_registered()`
ищет на диске подходящий TTF-шрифт в этом порядке:
`PDF_FONT_PATH` (env override) → DejaVu Sans (Linux/Docker, см.
`fonts-dejavu-core` в Dockerfile) → Liberation Sans → `C:\Windows\Fonts\
arial.ttf`/`times.ttf` (Windows — там кириллица и казахские буквы есть
из коробки) → шрифты macOS. Если ничего не найдено — используется
Helvetica с явным предупреждением в логах (лучше нечитаемый шрифт, чем
падение).

**Если вы разрабатываете локально на Windows** — ничего делать не нужно,
`arial.ttf`/`times.ttf` там уже есть и казахские буквы поддерживают.
**В Docker** — шрифт ставится автоматически через `fonts-dejavu-core` в
`Dockerfile`.

## 3. Архитектура

(см. предыдущую версию README — не изменилась: aiogram bot → Redis (arq)
→ worker → DOCX parser → Rule Engine → AI Analyzer → PDF → PostgreSQL/SQLite)


```
Telegram
   │
   ▼
 Bot (aiogram, long polling)  ──enqueue──▶  Redis (arq)  ──▶  Worker
   │                                                             │
   │ (только приём файла, быстрые ответы,                        ▼
   │  запись в БД, ничего тяжёлого)                DOCX parser → Rule Engine
   │                                                    → AI Analyzer → PDF
   ▼                                                             │
PostgreSQL/SQLite ◀──────────────────────────────────────────────┘
```

**Почему arq, а не Celery/RQ (спецификация §36):** проект целиком
асинхронный (aiogram 3.x, FastAPI, httpx/openai async client). arq —
asyncio-нативная очередь поверх того же Redis, который уже нужен для
идемпотентности/кеша, и job-функции пишутся в том же стиле `async def`,
что и остальной код. Celery/RQ синхронны по своей природе и потребовали бы
либо блокирующих вызовов, либо отдельного event loop bridging.

Модульная структура:

```
coursework_checker/
├── app/
│   ├── main.py                 # entrypoint бота (long polling)
│   ├── worker.py                # arq worker (тяжёлая обработка)
│   ├── queue.py                  # enqueue-обёртка над arq
│   ├── config/                   # settings, logging
│   ├── bot/                      # handlers / keyboards / states / middlewares
│   ├── api/                      # FastAPI — задел под будущий web/JSON API
│   ├── database/                 # SQLAlchemy models + repositories + session
│   ├── document/                 # DOCX parser, structure/heading detection, ooxml
│   ├── rules/                    # RulePreset модели, Rule Engine, 9 валидаторов
│   ├── ai/                       # LLMProvider абстракция, schemas, analyzer, chunking
│   ├── analysis/                 # pipeline, aggregator, scoring, similarity (интерфейс)
│   ├── reports/                  # PDF (ReportLab) + текстовые Telegram-представления
│   ├── security/                 # валидация файлов, безопасное хранилище
│   └── common/                   # enums, exceptions, shared Pydantic models, utils
├── prompts/                      # промпты для LLM — обычные .txt файлы, не хардкод
├── rules/presets/                # YAML-пресеты требований (админ-редактируемые)
├── migrations/                   # Alembic
├── tests/                        # unit + integration + генератор тестовых docx
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 3. Быстрый старт

```bash
git clone <repo>
cd coursework_checker
cp .env.example .env
# заполните минимум: BOT_TOKEN, ADMIN_IDS, LLM_API_KEY (или LLM_PROVIDER=mock для теста без ключа)
docker compose up --build
```

После первого запуска (или если меняли схему БД) примените миграции:

```bash
docker compose run --rm migrate
```

Откройте бота в Telegram и отправьте `.docx` файл.

### Локальный запуск без Docker (SQLite)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL по умолчанию — SQLite, Redis нужен локально
redis-server &          # или используйте Docker только для Redis
python -m app.main       # бот
arq app.worker.WorkerSettings   # в отдельном терминале — воркер
```

## 4. Переменные окружения (.env)

См. `.env.example`. Ключевые:

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | токен Telegram-бота |
| `ADMIN_IDS` | список telegram_id через запятую — роль ADMIN |
| `DATABASE_URL` | SQLite (dev) или PostgreSQL (prod) |
| `REDIS_URL` | брокер очереди задач |
| `LLM_PROVIDER` | `openai` \| `mock` (остальные — заглушки на будущее) |
| `LLM_API_KEY`, `LLM_MODEL` | доступ к LLM |
| `MAX_FILE_SIZE_MB`, `MAX_PAGES`, `MAX_AI_TOKENS_PER_CHECK`, `MAX_CHECKS_PER_DAY` | лимиты |
| `FILE_RETENTION_HOURS` | срок хранения временных файлов |
| `DEFAULT_RULE_PRESET` | пресет по умолчанию, если пользователь не выбрал явно |

**Никогда не коммитьте реальный `.env` в git.**

## 5. Добавление нового RulePreset (без кода!)

1. Скопируйте `rules/presets/makhambet_coursework.yaml`.
2. Измените `id`, `institution`, `work_type`, значения полей/шрифта/структуры.
3. Убедитесь, что `scoring.*` в сумме дают 100.
4. Перезапустите бота (или вызовите `PresetRegistry.reload()`).

Пример (сокращённо):

```yaml
id: makhambet_coursework
name: "Makhambet University — Курсовая работа"
institution: "Makhambet University"
work_type: coursework
margins: { top_mm: 20, bottom_mm: 20, left_mm: 30, right_mm: 10, tolerance_mm: 1.5 }
font: { name: "Times New Roman", size_pt: 14 }
paragraph: { alignment: justify, first_line_indent_cm: 1.25, line_spacing: 1.5 }
structure:
  required_sections: ["Введение", "Теоретическая часть", "Практическая часть", "Заключение", "Список литературы"]
scoring: { formatting: 30, structure: 20, language: 15, style: 10, content: 25 }
```

## 6. Настройка LLM

Абстракция `LLMProvider` (`app/ai/provider.py`) позволяет подключить любую
модель, реализовав один класс:

- `OpenAIProvider` — реализован полностью.
- `AnthropicProvider`, `GoogleProvider`, `LocalLLMProvider` — заготовки
  (`NotImplementedError`) для будущего подключения.
- `MockProvider` — используется в тестах и при `LLM_PROVIDER=mock`, не
  требует API-ключа, всегда возвращает пустой список ошибок.

Промпты — обычные `.txt` файлы в `prompts/` с явным форматом JSON-ответа
и инструкцией снижать `confidence` вместо выдумывания ошибок (спецификация
§32/§34).

## 7. Тестирование

```bash
pip install -r requirements.txt
pytest
```

Тесты используют `MockProvider`/стаб-провайдер — **не требуют реального
API-ключа и не обращаются в сеть**. Тестовые `.docx`-файлы (`correct.docx`,
`wrong_font.docx`, `wrong_margins.docx`, `wrong_spacing.docx`,
`missing_sections.docx`, `mixed_formatting.docx`) генерируются программно
через `tests/fixtures/generate_test_docs.py` при каждом запуске тестов —
бинарники не хранятся в git.

> **Примечание о статусе тестирования в этой поставке.** В среде, где
> собирался этот проект, не было доступа к интернету для `pip install`
> всех зависимостей (aiogram, sqlalchemy, pydantic и др. не были
> предустановлены). Модули, не зависящие от этих пакетов —
> `app/document/parser.py`, `app/document/structure.py`,
> `app/security/validation.py`, генератор тестовых `.docx` — были
> запущены и проверены вручную (страницы/поля/шрифты/структура
> определяются корректно). Остальной код синтаксически проверен
> (`python -m py_compile`) и прошёл ревью, но полный прогон `pytest`
> с реальными зависимостями нужно выполнить в вашем окружении перед
> продакшн-использованием — сделайте это первым шагом после `pip install`.

## 8. Миграции

```bash
alembic upgrade head                       # применить (включает 0002_add_user_language)
alembic revision --autogenerate -m "..."   # создать новую после правки моделей
```

**Если вы уже разворачивали БД раньше** (до появления выбора языка),
обязательно накатите миграции заново — иначе `users.language` не появится
и бот будет падать при попытке прочитать `db_user.language`:

```bash
docker compose run --rm migrate
# или локально:
alembic upgrade head
```

Для локальной разработки на SQLite `app/main.py` при старте сам создаёт
таблицы (`init_models()`), если `DATABASE_URL` начинается с `sqlite`. Для
PostgreSQL используйте только Alembic.

## 9. Приватность и безопасность (§24/§25)

- Разрешён только `.docx`; проверяется сигнатура ZIP, обязательные части
  OOXML, MIME-тип, защита от zip-slip/path traversal.
- Файл сохраняется под случайным именем во временной директории,
  права `0600`, автоматически удаляется после обработки и по истечении
  `FILE_RETENTION_HOURS` фоновой задачей.
- Полный текст документа **не логируется** и **не хранится** в БД —
  в БД остаются только числовые результаты и findings (короткие цитаты
  до 200 символов, только там, где это нужно для отчёта).
- Пользователю явно сообщается о политике хранения при `/start`.

## 10. Известные ограничения / что оставлено на будущее (§44)

Не реализовано в этой поставке (архитектура это закладывает, но код не
написан):

- Веб-интерфейс (React/Next.js) и личный кабинет — есть только базовый
  FastAPI `GET /api/v1/checks/{id}` как отправная точка.
- `AnthropicProvider` / `GoogleProvider` / `LocalLLMProvider` — заглушки.
- `SimilarityChecker` (проверка плагиата) — только протокол/интерфейс,
  без реализации. Бот **никогда** не заявляет, что проверяет плагиат.
- Batch-проверка (ZIP с 50 курсовыми), экспорт в Excel/CSV.
- Полноценная веб/UI админ-панель редактирования пресетов (сейчас —
  YAML-файлы + команды `/admin_stats`, `/admin_presets`).
- Кеширование повторных AI-запросов между проверками.

## 11. Troubleshooting

| Проблема | Решение |
|---|---|
| `RuntimeError: BOT_TOKEN is not set` | заполните `.env` |
| Бот не отвечает после отправки файла | проверьте, что запущен `worker` (`docker compose logs worker`) и Redis доступен |
| `RulePresetNotFoundError` | нет активного `.yaml` в `rules/presets/` с нужным `id`/`is_active: true` |
| AI-часть отчёта пустая / "AI-анализ выполнен частично" | проверьте `LLM_API_KEY`/`LLM_PROVIDER`, посмотрите логи воркера |
| PDF не создаётся | проверьте права на `REPORTS_DIR`, логи содержат `ReportGenerationError` |

---

Проект подготовлен как основа для дальнейшей доработки в коммерческий/
университетский продукт: модульная архитектура, admin-editable пресеты,
провайдеро-независимый AI-слой, единая структура результата (`CheckResult`),
пригодная для Telegram, PDF и будущего JSON API/веб-интерфейса.
