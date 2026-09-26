"""Central translation store.

Every string a user can see (Telegram messages, keyboard buttons, rule
findings, PDF report text) is looked up here by key, never hardcoded in a
single language elsewhere. This is what makes the bot's output follow the
user's chosen interface language end-to-end (spec: язык интерфейса kk/ru/en).

Usage:
    from app.i18n import t
    t("welcome", lang)
    t("margin.error", lang, label=t("label.left_margin", lang), expected="30 мм", actual="20 мм")
"""

from __future__ import annotations

DEFAULT_LANG = "ru"
SUPPORTED_LANGS = ("ru", "kk", "en")

# key -> {lang: template}. Templates use str.format placeholders.
MESSAGES: dict[str, dict[str, str]] = {
    # --- language selection ---
    "choose_language": {
        "ru": "🌐 Выберите язык интерфейса:",
        "kk": "🌐 Интерфейс тілін таңдаңыз:",
        "en": "🌐 Choose your interface language:",
    },
    "language_set": {
        "ru": "✅ Язык интерфейса: Русский",
        "kk": "✅ Интерфейс тілі: Қазақша",
        "en": "✅ Interface language: English",
    },
    # --- welcome / help ---
    "welcome": {
        "ru": (
            "👋 Добро пожаловать в Documentor — систему проверки курсовых и "
            "дипломных работ Makhambet University.\n\n"
            "Отправьте работу в формате .docx, и я проверю её оформление, "
            "структуру и содержание.\n\n"
            "ℹ️ Документ используется только для выполнения проверки и "
            "автоматически удаляется после завершения обработки согласно "
            "политике хранения."
        ),
        "kk": (
            "👋 Documentor жүйесіне қош келдіңіз — Makhambet University "
            "курстық және дипломдық жұмыстарын тексеру жүйесі.\n\n"
            "Жұмысты .docx форматында жіберіңіз, мен оның ресімделуін, "
            "құрылымын және мазмұнын тексеремін.\n\n"
            "ℹ️ Құжат тек тексеру үшін пайдаланылады және сақтау "
            "саясатына сәйкес өңдеу аяқталғаннан кейін автоматты түрде "
            "жойылады."
        ),
        "en": (
            "👋 Welcome to Documentor — the coursework and thesis review "
            "system for Makhambet University.\n\n"
            "Send your work as a .docx file and I'll check its formatting, "
            "structure and content.\n\n"
            "ℹ️ The document is used only to perform the check and is "
            "automatically deleted after processing, per our retention "
            "policy."
        ),
    },
    "help": {
        "ru": (
            "❓ Как это работает:\n\n"
            "1. Нажмите «📄 Проверить работу».\n"
            "2. Выберите тип работы (курсовая/дипломная).\n"
            "3. Отправьте файл .docx (до 20 МБ).\n"
            "4. Дождитесь завершения проверки.\n\n"
            "Проверка сочетает автоматический анализ оформления (шрифт, "
            "поля, отступы, структура) и AI-анализ текста (грамматика, "
            "стиль, содержание). Результаты AI носят рекомендательный "
            "характер."
        ),
        "kk": (
            "❓ Бұл қалай жұмыс істейді:\n\n"
            "1. «📄 Жұмысты тексеру» түймесін басыңыз.\n"
            "2. Жұмыс түрін таңдаңыз (курстық/дипломдық).\n"
            "3. .docx файлын жіберіңіз (20 МБ дейін).\n"
            "4. Тексеру аяқталғанша күтіңіз.\n\n"
            "Тексеру ресімдеуді автоматты талдауды (қаріп, жиектер, "
            "шегіністер, құрылым) және мәтінді AI арқылы талдауды "
            "(грамматика, стиль, мазмұн) біріктіреді. AI нәтижелері "
            "ұсыныс сипатында болады."
        ),
        "en": (
            "❓ How it works:\n\n"
            "1. Tap “📄 Check my work”.\n"
            "2. Choose the work type (coursework/thesis).\n"
            "3. Send a .docx file (up to 20 MB).\n"
            "4. Wait for the check to finish.\n\n"
            "The check combines automatic formatting analysis (font, "
            "margins, indents, structure) with AI text analysis (grammar, "
            "style, content). AI results are advisory, not authoritative."
        ),
    },
    # --- main menu ---
    "menu.check_new": {
        "ru": "📄 Проверить работу",
        "kk": "📄 Жұмысты тексеру",
        "en": "📄 Check my work",
    },
    "menu.history": {
        "ru": "📋 История проверок",
        "kk": "📋 Тексерулер тарихы",
        "en": "📋 Check history",
    },
    "menu.settings": {"ru": "⚙️ Настройки", "kk": "⚙️ Баптаулар", "en": "⚙️ Settings"},
    "menu.help": {"ru": "❓ Помощь", "kk": "❓ Көмек", "en": "❓ Help"},
    "menu.language": {"ru": "🌐 Язык", "kk": "🌐 Тіл", "en": "🌐 Language"},
    # --- work type selection ---
    "ask_work_type": {
        "ru": "📚 Выберите тип работы:",
        "kk": "📚 Жұмыс түрін таңдаңыз:",
        "en": "📚 Choose the work type:",
    },
    "work_type.coursework": {"ru": "📚 Курсовая", "kk": "📚 Курстық жұмыс", "en": "📚 Coursework"},
    "work_type.diploma": {"ru": "🎓 Дипломная", "kk": "🎓 Дипломдық жұмыс", "en": "🎓 Thesis"},
    "work_type.report": {
        "ru": "📝 Отчёт по практике",
        "kk": "📝 Практика есебі",
        "en": "📝 Practice report",
    },
    "work_type.essay": {"ru": "📃 Реферат", "kk": "📃 Реферат", "en": "📃 Essay"},
    "work_type_chosen": {
        "ru": "✅ Выбрано: {preset_name}.\n\n📎 Теперь отправьте файл .docx для проверки.",
        "kk": "✅ Таңдалды: {preset_name}.\n\n📎 Енді тексеру үшін .docx файлын жіберіңіз.",
        "en": "✅ Selected: {preset_name}.\n\n📎 Now send a .docx file to check.",
    },
    "no_presets_configured": {
        "ru": "⚠️ Не настроено ни одного набора требований. Обратитесь к администратору.",
        "kk": "⚠️ Талаптар жиынтығы теңшелмеген. Әкімшіге хабарласыңыз.",
        "en": "⚠️ No requirement presets are configured. Please contact the administrator.",
    },
    "wrong_content_type": {
        "ru": "❌ Пожалуйста, отправьте файл в формате .docx.",
        "kk": "❌ .docx форматындағы файлды жіберіңіз.",
        "en": "❌ Please send a file in .docx format.",
    },
    # --- document upload flow ---
    "file_received": {
        "ru": "📄 Файл получен.\n\nНазвание: {filename}\nРазмер: {size} MB",
        "kk": "📄 Файл қабылданды.\n\nАты: {filename}\nӨлшемі: {size} MB",
        "en": "📄 File received.\n\nName: {filename}\nSize: {size} MB",
    },
    "check_starting": {
        "ru": "⏳ Начинаю проверку…",
        "kk": "⏳ Тексеру басталды…",
        "en": "⏳ Starting the check…",
    },
    "stage.structure": {
        "ru": "🔍 Анализирую структуру документа…",
        "kk": "🔍 Құжат құрылымын талдап жатырмын…",
        "en": "🔍 Analyzing document structure…",
    },
    "stage.formatting": {
        "ru": "📐 Проверяю оформление…",
        "kk": "📐 Ресімдеуді тексеріп жатырмын…",
        "en": "📐 Checking formatting…",
    },
    "stage.text": {
        "ru": "📝 Анализирую текст…",
        "kk": "📝 Мәтінді талдап жатырмын…",
        "en": "📝 Analyzing the text…",
    },
    "stage.ai": {
        "ru": "🤖 Проверяю содержание с помощью ИИ…",
        "kk": "🤖 Мазмұнды AI көмегімен тексеріп жатырмын…",
        "en": "🤖 Reviewing content with AI…",
    },
    "stage.report": {
        "ru": "📊 Формирую итоговый отчёт…",
        "kk": "📊 Қорытынды есепті қалыптастырып жатырмын…",
        "en": "📊 Building the final report…",
    },
    "delivery.sent": {
        "ru": "✅ Проверка завершена. Отчёт отправлен ниже.",
        "kk": "✅ Тексеру аяқталды. Есеп төменде жіберілді.",
        "en": "✅ Check completed. The report has been sent below.",
    },
    "delivery.failed": {
        "ru": "⚠️ Проверка завершена, но отправить PDF не удалось. Результат сохранён. Обратитесь к администратору для повторной отправки.",
        "kk": "⚠️ Тексеру аяқталды, бірақ PDF жіберілмеді. Нәтиже сақталды. Қайта жіберу үшін әкімшіге хабарласыңыз.",
        "en": "⚠️ Check completed, but PDF delivery failed. The result is saved. Contact the administrator to retry delivery.",
    },
    # --- results ---
    "summary.title": {
        "ru": "✅ Проверка завершена.",
        "kk": "✅ Тексеру аяқталды.",
        "en": "✅ Check completed.",
    },
    "summary.score": {
        "ru": "Результат: {score:.0f}/{max_score:.0f}",
        "kk": "Нәтиже: {score:.0f}/{max_score:.0f}",
        "en": "Score: {score:.0f}/{max_score:.0f}",
    },
    "summary.critical": {
        "ru": "🔴 Критические ошибки: {n}",
        "kk": "🔴 Сыни қателер: {n}",
        "en": "🔴 Critical errors: {n}",
    },
    "summary.errors": {
        "ru": "🟠 Ошибки оформления: {n}",
        "kk": "🟠 Ресімдеу қателері: {n}",
        "en": "🟠 Formatting errors: {n}",
    },
    "summary.warnings": {
        "ru": "🟡 Замечания: {n}",
        "kk": "🟡 Ескертулер: {n}",
        "en": "🟡 Warnings: {n}",
    },
    "summary.passed": {
        "ru": "🟢 Соответствует требованиям: {n}",
        "kk": "🟢 Талаптарға сай: {n}",
        "en": "🟢 Meets requirements: {n}",
    },
    "summary.ai_partial": {
        "ru": "⚠️ AI-анализ текста выполнен частично.\n\n",
        "kk": "⚠️ Мәтіннің AI талдауы жартылай орындалды.\n\n",
        "en": "⚠️ AI text analysis was only partially completed.\n\n",
    },
    "summary.footer": {
        "ru": "Ниже доступен подробный отчёт.",
        "kk": "Төменде толық есеп қолжетімді.",
        "en": "The detailed report is available below.",
    },
    "results.category_scores_title": {
        "ru": "📊 Результат по категориям:",
        "kk": "📊 Санаттар бойынша нәтиже:",
        "en": "📊 Results by category:",
    },
    "results.total": {
        "ru": "Итого: {score:.0f}/{max_score:.0f}",
        "kk": "Барлығы: {score:.0f}/{max_score:.0f}",
        "en": "Total: {score:.0f}/{max_score:.0f}",
    },
    "errors.title": {
        "ru": "❌ Найденные ошибки:\n",
        "kk": "❌ Табылған қателер:\n",
        "en": "❌ Errors found:\n",
    },
    "errors.none": {
        "ru": "🎉 Критических ошибок и ошибок оформления не обнаружено.",
        "kk": "🎉 Сыни және ресімдеу қателері табылған жоқ.",
        "en": "🎉 No critical or formatting errors were found.",
    },
    "errors.more": {
        "ru": "…и ещё {n} ошибок. Полный список — в PDF-отчёте.",
        "kk": "…тағы {n} қате. Толық тізім — PDF есепте.",
        "en": "…and {n} more errors. See the full list in the PDF report.",
    },
    "recommendations.title": {
        "ru": "💡 Рекомендации по исправлению:\n",
        "kk": "💡 Түзету бойынша ұсыныстар:\n",
        "en": "💡 Recommendations:\n",
    },
    "recommendations.none": {
        "ru": "На данный момент дополнительных рекомендаций нет.",
        "kk": "Қазіргі уақытта қосымша ұсыныстар жоқ.",
        "en": "There are no additional recommendations at this time.",
    },
    "recommendations.more": {
        "ru": "\n…и ещё {n} рекомендаций. Полный список — в PDF-отчёте.",
        "kk": "\n…тағы {n} ұсыныс. Толық тізім — PDF есепте.",
        "en": "\n…and {n} more recommendations. See the full list in the PDF report.",
    },
    "confidence_label": {
        "ru": "Уверенность AI: {pct}%",
        "kk": "AI сенімділігі: {pct}%",
        "en": "AI confidence: {pct}%",
    },
    "source.rule_engine": {
        "ru": "Источник: автоматическая проверка документа",
        "kk": "Дереккөз: құжатты автоматты тексеру",
        "en": "Source: automated document check",
    },
    "source.ai": {
        "ru": "Источник: AI-анализ",
        "kk": "Дереккөз: AI талдауы",
        "en": "Source: AI analysis",
    },
    # --- history / settings ---
    "history.empty": {
        "ru": "📋 История проверок пуста.",
        "kk": "📋 Тексерулер тарихы бос.",
        "en": "📋 Your check history is empty.",
    },
    "history.title": {
        "ru": "📋 История проверок:\n",
        "kk": "📋 Тексерулер тарихы:\n",
        "en": "📋 Check history:\n",
    },
    "settings.text": {
        "ru": (
            "⚙️ Настройки\n\n"
            "🔒 Политика хранения данных:\n"
            "Загруженные документы используются только для проверки и "
            "автоматически удаляются после завершения обработки. Полный "
            "текст работы не сохраняется в базе данных — сохраняются "
            "только результаты проверки.\n\n"
            "Чтобы выбрать другой тип работы, нажмите «📄 Проверить работу» "
            "в главном меню, а чтобы сменить язык — «🌐 Язык»."
        ),
        "kk": (
            "⚙️ Баптаулар\n\n"
            "🔒 Деректерді сақтау саясаты:\n"
            "Жүктелген құжаттар тек тексеру үшін пайдаланылады және "
            "өңдеу аяқталғаннан кейін автоматты түрде жойылады. Жұмыстың "
            "толық мәтіні дерекқорда сақталмайды — тек тексеру нәтижелері "
            "сақталады.\n\n"
            "Басқа жұмыс түрін таңдау үшін негізгі мәзірдегі «📄 Жұмысты "
            "тексеру» түймесін, ал тілді ауыстыру үшін «🌐 Тіл» түймесін "
            "басыңыз."
        ),
        "en": (
            "⚙️ Settings\n\n"
            "🔒 Data retention policy:\n"
            "Uploaded documents are used only to run the check and are "
            "automatically deleted after processing. The full text of "
            "your work is never stored in the database — only the check "
            "results are.\n\n"
            "To choose a different work type, tap “📄 Check my work” in "
            "the main menu; to change the language, tap “🌐 Language”."
        ),
    },
    # --- errors / limits ---
    "error.daily_limit": {
        "ru": "⚠️ Вы достигли дневного лимита проверок. Попробуйте завтра.",
        "kk": "⚠️ Күндізгі тексеру лимитіне жеттіңіз. Ертең қайталап көріңіз.",
        "en": "⚠️ You've reached your daily check limit. Please try again tomorrow.",
    },
    "error.file_too_large": {
        "ru": "❌ Файл слишком большой.",
        "kk": "❌ Файл тым үлкен.",
        "en": "❌ The file is too large.",
    },
    "error.unsupported_format": {
        "ru": "❌ Неподдерживаемый формат. Отправьте файл .docx.",
        "kk": "❌ Қолдау көрсетілмейтін формат. .docx файлын жіберіңіз.",
        "en": "❌ Unsupported format. Please send a .docx file.",
    },
    "error.corrupted_document": {
        "ru": "❌ Не удалось открыть документ — файл повреждён.",
        "kk": "❌ Құжатты ашу мүмкін болмады — файл зақымдалған.",
        "en": "❌ Could not open the document — the file appears to be corrupted.",
    },
    "error.text_extraction": {
        "ru": "❌ Не удалось извлечь текст из документа.",
        "kk": "❌ Құжаттан мәтінді алу мүмкін болмады.",
        "en": "❌ Could not extract text from the document.",
    },
    "error.too_many_pages": {
        "ru": "❌ Документ превышает максимально допустимое количество страниц.",
        "kk": "❌ Құжат рұқсат етілген максималды бет санынан асып кетті.",
        "en": "❌ The document exceeds the maximum allowed number of pages.",
    },
    "error.preset_not_found": {
        "ru": "⚠️ Не удалось найти набор требований. Обратитесь к администратору.",
        "kk": "⚠️ Талаптар жиынтығы табылмады. Әкімшіге хабарласыңыз.",
        "en": "⚠️ Could not find the requirement preset. Please contact the administrator.",
    },
    "error.ai_provider": {
        "ru": "❌ Ошибка при AI-анализе. Результаты по оформлению и структуре доступны.",
        "kk": "❌ AI талдауында қате орын алды. Ресімдеу мен құрылым нәтижелері қолжетімді.",
        "en": "❌ An error occurred during AI analysis. Formatting and structure results are still available.",
    },
    "error.ai_quota": {
        "ru": "❌ Превышен лимит обращений к AI-сервису. Попробуйте позже.",
        "kk": "❌ AI қызметіне сұраулар лимиті асып кетті. Кейінірек қайталап көріңіз.",
        "en": "❌ The AI service request limit was exceeded. Please try again later.",
    },
    "error.report_generation": {
        "ru": "⚠️ Не удалось сформировать PDF-отчёт, но результаты проверки доступны.",
        "kk": "⚠️ PDF есепті қалыптастыру мүмкін болмады, бірақ тексеру нәтижелері қолжетімді.",
        "en": "⚠️ Could not generate the PDF report, but the check results are still available.",
    },
    "error.security": {
        "ru": "❌ Файл не прошёл проверку безопасности.",
        "kk": "❌ Файл қауіпсіздік тексеруінен өтпеді.",
        "en": "❌ The file failed the security check.",
    },
    "error.internal": {
        "ru": "⚠️ Не удалось завершить проверку. Попробуйте повторить позже.",
        "kk": "⚠️ Тексеруді аяқтау мүмкін болмады. Кейінірек қайталап көріңіз.",
        "en": "⚠️ Could not complete the check. Please try again later.",
    },
    "check_not_found": {
        "ru": "⚠️ Результаты проверки не найдены.",
        "kk": "⚠️ Тексеру нәтижелері табылмады.",
        "en": "⚠️ Check results not found.",
    },
    "pdf_not_available": {
        "ru": "⚠️ PDF-отчёт больше не доступен.",
        "kk": "⚠️ PDF есеп енді қолжетімді емес.",
        "en": "⚠️ The PDF report is no longer available.",
    },
    "pdf_caption": {
        "ru": "📄 Подробный PDF-отчёт",
        "kk": "📄 Толық PDF есеп",
        "en": "📄 Detailed PDF report",
    },
    # --- result menu buttons ---
    "btn.result_scores": {"ru": "📊 Результат", "kk": "📊 Нәтиже", "en": "📊 Score"},
    "btn.result_errors": {"ru": "❌ Ошибки", "kk": "❌ Қателер", "en": "❌ Errors"},
    "btn.result_recommendations": {
        "ru": "💡 Рекомендации",
        "kk": "💡 Ұсыныстар",
        "en": "💡 Recommendations",
    },
    "btn.result_pdf": {"ru": "📄 Скачать PDF", "kk": "📄 PDF жүктеу", "en": "📄 Download PDF"},
    "btn.result_new_check": {
        "ru": "🔄 Проверить другой файл",
        "kk": "🔄 Басқа файлды тексеру",
        "en": "🔄 Check another file",
    },
    # --- admin ---
    "admin.only": {
        "ru": "⛔ Эта команда доступна только администраторам.",
        "kk": "⛔ Бұл команда тек әкімшілерге қолжетімді.",
        "en": "⛔ This command is only available to administrators.",
    },
    # --- category labels (used in results + PDF table) ---
    "category.formatting": {"ru": "Оформление", "kk": "Ресімдеу", "en": "Formatting"},
    "category.structure": {"ru": "Структура", "kk": "Құрылым", "en": "Structure"},
    "category.language": {"ru": "Язык", "kk": "Тіл", "en": "Language"},
    "category.style": {"ru": "Стиль", "kk": "Стиль", "en": "Style"},
    "category.content": {"ru": "Содержание", "kk": "Мазмұны", "en": "Content"},
    # --- PDF report ---
    "pdf.title": {"ru": "ОТЧЁТ ПРОВЕРКИ", "kk": "ТЕКСЕРУ ЕСЕБІ", "en": "REVIEW REPORT"},
    "pdf.file": {"ru": "Файл", "kk": "Файл", "en": "File"},
    "pdf.institution": {"ru": "Учебное заведение", "kk": "Оқу орны", "en": "Institution"},
    "pdf.work_type": {"ru": "Тип работы", "kk": "Жұмыс түрі", "en": "Work type"},
    "pdf.date": {"ru": "Дата проверки", "kk": "Тексеру күні", "en": "Check date"},
    "pdf.total": {"ru": "Итог", "kk": "Қорытынды", "en": "Total"},
    "pdf.section1": {
        "ru": "1. ОБЩИЙ РЕЗУЛЬТАТ",
        "kk": "1. ЖАЛПЫ НӘТИЖЕ",
        "en": "1. OVERALL RESULT",
    },
    "pdf.table.category": {"ru": "Категория", "kk": "Санат", "en": "Category"},
    "pdf.table.points": {"ru": "Баллы", "kk": "Балл", "en": "Points"},
    "pdf.section2": {
        "ru": "2. ОШИБКИ ОФОРМЛЕНИЯ",
        "kk": "2. РЕСІМДЕУ ҚАТЕЛЕРІ",
        "en": "2. FORMATTING ERRORS",
    },
    "pdf.section2.none": {
        "ru": "Ошибок оформления не обнаружено.",
        "kk": "Ресімдеу қателері табылған жоқ.",
        "en": "No formatting errors were found.",
    },
    "pdf.section3": {
        "ru": "3. СТРУКТУРА И ЛИТЕРАТУРА",
        "kk": "3. ҚҰРЫЛЫМ ЖӘНЕ ӘДЕБИЕТТЕР",
        "en": "3. STRUCTURE AND REFERENCES",
    },
    "pdf.section3.none": {
        "ru": "Замечаний по структуре не обнаружено.",
        "kk": "Құрылым бойынша ескертулер табылған жоқ.",
        "en": "No structural issues were found.",
    },
    "pdf.section4": {
        "ru": "4. АНАЛИЗ ТЕКСТА (AI)",
        "kk": "4. МӘТІНДІ ТАЛДАУ (AI)",
        "en": "4. TEXT ANALYSIS (AI)",
    },
    "pdf.section4.partial": {
        "ru": "⚠️ AI-анализ текста выполнен частично или недоступен для части документа.",
        "kk": "⚠️ Мәтіннің AI талдауы ішінара орындалды немесе құжаттың бір бөлігі үшін қолжетімсіз.",
        "en": "⚠️ AI text analysis was only partially completed or unavailable for part of the document.",
    },
    "pdf.section4.none": {
        "ru": "Существенных замечаний по тексту не обнаружено.",
        "kk": "Мәтін бойынша елеулі ескертулер табылған жоқ.",
        "en": "No significant text issues were found.",
    },
    "pdf.quote_label": {"ru": "Исходный текст", "kk": "Түпнұсқа мәтін", "en": "Original text"},
    "pdf.expected_actual": {
        "ru": "Требуется: {expected} — Обнаружено: {actual}",
        "kk": "Талап етіледі: {expected} — Анықталды: {actual}",
        "en": "Required: {expected} — Found: {actual}",
    },
    "pdf.footer": {
        "ru": (
            "Документ использовался только для выполнения проверки и "
            "автоматически удаляется после завершения обработки согласно "
            "политике хранения. Результаты AI-анализа носят "
            "рекомендательный характер и не заменяют проверку научным "
            "руководителем."
        ),
        "kk": (
            "Құжат тек тексеру үшін пайдаланылды және сақтау саясатына "
            "сәйкес өңдеу аяқталғаннан кейін автоматты түрде жойылады. "
            "AI талдауының нәтижелері ұсыныс сипатында болады және "
            "ғылыми жетекшінің тексеруін алмастырмайды."
        ),
        "en": (
            "The document was used only to perform this check and is "
            "automatically deleted after processing, per our retention "
            "policy. AI analysis results are advisory and do not replace "
            "review by your academic supervisor."
        ),
    },
    # --- rule engine: labels ---
    "label.left_margin": {"ru": "Левое поле", "kk": "Сол жақ жиек", "en": "Left margin"},
    "label.right_margin": {"ru": "Правое поле", "kk": "Оң жақ жиек", "en": "Right margin"},
    "label.top_margin": {"ru": "Верхнее поле", "kk": "Жоғарғы жиек", "en": "Top margin"},
    "label.bottom_margin": {"ru": "Нижнее поле", "kk": "Төменгі жиек", "en": "Bottom margin"},
    "label.page_params": {
        "ru": "Параметры страницы",
        "kk": "Бет параметрлері",
        "en": "Page settings",
    },
    "label.headers_footers": {"ru": "Колонтитулы", "kk": "Колонтитулдар", "en": "Headers/footers"},
    "label.main_text": {"ru": "Основной текст", "kk": "Негізгі мәтін", "en": "Main text"},
    "label.whole_document": {
        "ru": "По всему документу",
        "kk": "Бүкіл құжат бойынша",
        "en": "Throughout the document",
    },
    "label.paragraphs": {
        "ru": "Абзацы №{list}",
        "kk": "{list}-абзацтар",
        "en": "Paragraphs #{list}",
    },
    "label.introduction": {"ru": "Введение", "kk": "Кіріспе", "en": "Introduction"},
    # --- rule engine: page/margins ---
    "rule.page_size.error": {
        "ru": "Размер страницы не соответствует формату A4.",
        "kk": "Бет өлшемі A4 форматына сәйкес келмейді.",
        "en": "Page size does not match the A4 format.",
    },
    "rule.page_size.pass": {
        "ru": "Размер страницы соответствует A4.",
        "kk": "Бет өлшемі A4-ке сәйкес келеді.",
        "en": "Page size matches A4.",
    },
    "rule.orientation.error": {
        "ru": "Ориентация страницы не соответствует требованиям.",
        "kk": "Бет бағыты талаптарға сәйкес келмейді.",
        "en": "Page orientation does not meet the requirements.",
    },
    "rule.orientation.pass": {
        "ru": "Ориентация страницы верная.",
        "kk": "Бет бағыты дұрыс.",
        "en": "Page orientation is correct.",
    },
    "rule.header_footer.present": {
        "ru": "Колонтитулы обнаружены.",
        "kk": "Колонтитулдар табылды.",
        "en": "Headers/footers were found.",
    },
    "rule.header_footer.absent": {
        "ru": "Колонтитулы не обнаружены.",
        "kk": "Колонтитулдар табылмады.",
        "en": "No headers/footers were found.",
    },
    "rule.margin.error": {
        "ru": "{label} не соответствует требованиям.",
        "kk": "{label} талаптарға сәйкес келмейді.",
        "en": "{label} does not meet the requirements.",
    },
    "rule.margin.pass": {
        "ru": "{label} соответствует требованиям.",
        "kk": "{label} талаптарға сәйкес келеді.",
        "en": "{label} meets the requirements.",
    },
    # --- rule engine: font ---
    "rule.font.undetected": {
        "ru": "Не удалось определить шрифт документа.",
        "kk": "Құжат қарпін анықтау мүмкін болмады.",
        "en": "Could not determine the document's font.",
    },
    "rule.font.main.pass": {
        "ru": "Основной шрифт соответствует требованиям ({name}, {size} pt).",
        "kk": "Негізгі қаріп талаптарға сәйкес келеді ({name}, {size} pt).",
        "en": "The main font meets the requirements ({name}, {size} pt).",
    },
    "rule.font.main.error": {
        "ru": "Основной шрифт документа не соответствует требованиям.",
        "kk": "Құжаттың негізгі қарпі талаптарға сәйкес келмейді.",
        "en": "The document's main font does not meet the requirements.",
    },
    "rule.font.mixed": {
        "ru": "Документ содержит фрагменты с неправильным шрифтом.",
        "kk": "Құжатта қате қаріппен жазылған үзінділер бар.",
        "en": "The document contains fragments with an incorrect font.",
    },
    "rule.font.paragraph_consistency": {
        "ru": "В указанных абзацах шрифт отличается от требуемого.",
        "kk": "Көрсетілген абзацтарда қаріп талап етілгеннен өзгеше.",
        "en": "The font in the listed paragraphs differs from the required one.",
    },
    # --- rule engine: spacing / paragraphs ---
    "rule.line_spacing.error": {
        "ru": "Межстрочный интервал не соответствует требованиям.",
        "kk": "Жол аралығы талаптарға сәйкес келмейді.",
        "en": "Line spacing does not meet the requirements.",
    },
    "rule.line_spacing.pass": {
        "ru": "Межстрочный интервал соответствует требованиям.",
        "kk": "Жол аралығы талаптарға сәйкес келеді.",
        "en": "Line spacing meets the requirements.",
    },
    "rule.first_line_indent.error": {
        "ru": "Отступ первой строки настроен неправильно.",
        "kk": "Бірінші жол шегінісі дұрыс орнатылмаған.",
        "en": "The first-line indent is set incorrectly.",
    },
    "rule.first_line_indent.pass": {
        "ru": "Отступ первой строки соответствует требованиям.",
        "kk": "Бірінші жол шегінісі талаптарға сәйкес келеді.",
        "en": "The first-line indent meets the requirements.",
    },
    "rule.alignment.error": {
        "ru": "Выравнивание текста не соответствует требованиям.",
        "kk": "Мәтін туралануы талаптарға сәйкес келмейді.",
        "en": "Text alignment does not meet the requirements.",
    },
    "rule.alignment.pass": {
        "ru": "Выравнивание текста соответствует требованиям.",
        "kk": "Мәтін туралануы талаптарға сәйкес келеді.",
        "en": "Text alignment meets the requirements.",
    },
    "rule.side_indent": {
        "ru": "Обнаружены нестандартные боковые отступы абзацев.",
        "kk": "Абзацтарда стандартты емес бүйір шегіністер табылды.",
        "en": "Non-standard side indents were found in paragraphs.",
    },
    # --- rule engine: headings / numbering ---
    "rule.heading.too_deep": {
        "ru": "Обнаружены заголовки глубже допустимого уровня ({max_level}).",
        "kk": "Рұқсат етілген деңгейден ({max_level}) тереңірек тақырыптар табылды.",
        "en": "Headings deeper than the allowed level ({max_level}) were found.",
    },
    "rule.heading.unnumbered": {
        "ru": "Некоторые заголовки не пронумерованы.",
        "kk": "Кейбір тақырыптар нөмірленбеген.",
        "en": "Some headings are not numbered.",
    },
    "rule.heading.none_found": {
        "ru": "В документе не найдено ни одного заголовка, оформленного стилем.",
        "kk": "Құжатта стильмен ресімделген бірде-бір тақырып табылмады.",
        "en": "No headings formatted with a heading style were found in the document.",
    },
    "rule.heading.none_found.suggestion": {
        "ru": "Используйте стили 'Заголовок 1/2/3' вместо ручного форматирования.",
        "kk": "Қолмен пішімдеудің орнына 'Тақырып 1/2/3' стильдерін пайдаланыңыз.",
        "en": "Use 'Heading 1/2/3' styles instead of manual formatting.",
    },
    "rule.heading.found": {
        "ru": "Обнаружено заголовков: {n}.",
        "kk": "Табылған тақырыптар саны: {n}.",
        "en": "Headings found: {n}.",
    },
    "rule.numbering.ok": {
        "ru": "Нумерация заголовков корректна.",
        "kk": "Тақырыптардың нөмірленуі дұрыс.",
        "en": "Heading numbering is correct.",
    },
    "rule.numbering.sequence_error": {
        "ru": "Нарушена последовательность нумерации разделов: {prev} -> {curr}",
        "kk": "Бөлімдер нөмірленуінің реттілігі бұзылған: {prev} -> {curr}",
        "en": "The section numbering sequence is broken: {prev} -> {curr}",
    },
    "rule.numbering.level_jump": {
        "ru": "Заголовок «{heading}» пропускает уровень вложенности (с уровня {prev} на {curr})",
        "kk": "«{heading}» тақырыбы тереңдік деңгейін өткізіп жіберді ({prev}-ден {curr}-ге дейін)",
        "en": "Heading “{heading}” skips a nesting level (from level {prev} to {curr})",
    },
    # --- rule engine: structure ---
    "rule.structure.section_present": {
        "ru": "Раздел «{label}» присутствует.",
        "kk": "«{label}» бөлімі бар.",
        "en": "Section “{label}” is present.",
    },
    "rule.structure.section_missing": {
        "ru": "Обязательный раздел «{label}» отсутствует.",
        "kk": "Міндетті «{label}» бөлімі жоқ.",
        "en": "The required section “{label}” is missing.",
    },
    "rule.structure.section_missing.suggestion": {
        "ru": "Добавьте раздел «{label}», оформленный стилем заголовка.",
        "kk": "Тақырып стилімен ресімделген «{label}» бөлімін қосыңыз.",
        "en": "Add a section “{label}” formatted with a heading style.",
    },
    "rule.structure.optional_missing": {
        "ru": "Необязательный раздел «{label}» не обнаружен.",
        "kk": "Міндетті емес «{label}» бөлімі табылмады.",
        "en": "The optional section “{label}” was not found.",
    },
    # --- rule engine: references ---
    "rule.references.missing": {
        "ru": "Список литературы отсутствует.",
        "kk": "Әдебиеттер тізімі жоқ.",
        "en": "The list of references is missing.",
    },
    "rule.references.min_count": {
        "ru": "Недостаточное количество источников в списке литературы.",
        "kk": "Әдебиеттер тізіміндегі дереккөздер саны жеткіліксіз.",
        "en": "The list of references does not have enough sources.",
    },
    "rule.references.count": {
        "ru": "Обнаружено источников: {n}.",
        "kk": "Табылған дереккөздер саны: {n}.",
        "en": "Sources found: {n}.",
    },
    "rule.references.duplicates": {
        "ru": "В списке литературы обнаружены повторяющиеся записи ({n}).",
        "kk": "Әдебиеттер тізімінде қайталанатын жазбалар табылды ({n}).",
        "en": "Duplicate entries were found in the reference list ({n}).",
    },
    "rule.references.suspicious": {
        "ru": "Обнаружены подозрительно короткие/пустые записи: {n}.",
        "kk": "Күдікті қысқа/бос жазбалар табылды: {n}.",
        "en": "Suspiciously short/empty entries were found: {n}.",
    },
    "rule.references.in_text_missing": {
        "ru": "В тексте не найдено ссылок на источники в формате [номер].",
        "kk": "Мәтінде [нөмір] форматындағы дереккөздерге сілтемелер табылмады.",
        "en": "No in-text citations in the [number] format were found.",
    },
    "rule.references.in_text_found": {
        "ru": "Найдено ссылок на источники в тексте: {n}.",
        "kk": "Мәтінде табылған дереккөздерге сілтемелер: {n}.",
        "en": "In-text citations found: {n}.",
    },
    # --- section labels used in structure/references messages ---
    "section.introduction": {"ru": "Введение", "kk": "Кіріспе", "en": "Introduction"},
    "section.theoretical_part": {
        "ru": "Теоретическая часть",
        "kk": "Теориялық бөлім",
        "en": "Theoretical part",
    },
    "section.practical_part": {
        "ru": "Практическая часть",
        "kk": "Практикалық бөлім",
        "en": "Practical part",
    },
    "section.main_body": {"ru": "Основная часть", "kk": "Негізгі бөлім", "en": "Main body"},
    "section.conclusion": {"ru": "Заключение", "kk": "Қорытынды", "en": "Conclusion"},
    "section.references": {
        "ru": "Список литературы",
        "kk": "Әдебиеттер тізімі",
        "en": "List of references",
    },
    "section.appendix": {"ru": "Приложение", "kk": "Қосымша", "en": "Appendix"},
    "section.abstract": {"ru": "Аннотация", "kk": "Аңдатпа", "en": "Abstract"},
    # --- AI: introduction structural elements ---
    "label.ai.relevance": {"ru": "актуальность", "kk": "өзектілік", "en": "relevance"},
    "label.ai.problem": {
        "ru": "проблема исследования",
        "kk": "зерттеу мәселесі",
        "en": "research problem",
    },
    "label.ai.aim": {"ru": "цель", "kk": "мақсат", "en": "aim"},
    "label.ai.tasks": {"ru": "задачи", "kk": "міндеттер", "en": "tasks"},
    "label.ai.object": {
        "ru": "объект исследования",
        "kk": "зерттеу объектісі",
        "en": "research object",
    },
    "label.ai.subject": {
        "ru": "предмет исследования",
        "kk": "зерттеу пәні",
        "en": "research subject",
    },
    "label.ai.methods": {
        "ru": "методы исследования",
        "kk": "зерттеу әдістері",
        "en": "research methods",
    },
    "ai.introduction.complete": {
        "ru": "Введение содержит все обязательные смысловые элементы.",
        "kk": "Кіріспеде барлық міндетті мазмұндық элементтер бар.",
        "en": "The introduction contains all required structural elements.",
    },
    "ai.introduction.missing": {
        "ru": "Во введении не выявлены элементы: {elements}.",
        "kk": "Кіріспеде мына элементтер анықталмады: {elements}.",
        "en": "The introduction is missing these elements: {elements}.",
    },
    "ai.introduction.missing.suggestion": {
        "ru": "Убедитесь, что каждый элемент явно сформулирован во введении.",
        "kk": "Әр элемент кіріспеде нақты тұжырымдалғанына көз жеткізіңіз.",
        "en": "Make sure each element is explicitly stated in the introduction.",
    },
}


MESSAGES.update(
    {
        "not_evaluated": {"ru": "Не проверено", "kk": "Тексерілмеді", "en": "Not evaluated"},
        "rule.min_words": {
            "ru": "Раздел короче требуемого объёма.",
            "kk": "Бөлім көлемі талаптан аз.",
            "en": "Section is shorter than required.",
        },
        "rule.page_break": {
            "ru": "Перед разделом нужен явный разрыв страницы.",
            "kk": "Бөлім алдында бет үзілісі қажет.",
            "en": "An explicit page break is required before this section.",
        },
        "rule.heading_bold": {
            "ru": "Полужирный заголовок запрещён выбранными требованиями.",
            "kk": "Талаптар бойынша қалың тақырыпқа рұқсат жоқ.",
            "en": "Bold headings are not allowed by this preset.",
        },
        "history.deleted": {
            "ru": "Удалено завершённых проверок: {n}. Активные проверки сохранены.",
            "kk": "Аяқталған тексерулер жойылды: {n}. Белсенді тексерулер сақталды.",
            "en": "Deleted completed checks: {n}. Active checks were retained.",
        },
    }
)


MESSAGES.update({
    "section.content_table": {"ru": "Содержание", "kk": "Мазмұны", "en": "Table of contents"},
    "ai.reason.budget": {"ru": "Достигнут лимит объёма проверки текста.", "kk": "Мәтінді тексеру көлемінің шегіне жетті.", "en": "The text review budget was reached."},
    "ai.reason.timeout": {"ru": "Сервис не успел завершить проверку текста.", "kk": "Мәтінді тексеру уақытында аяқталмады.", "en": "Text review reached its time limit."},
    "ai.reason.provider": {"ru": "Часть запросов к сервису проверки текста не выполнена.", "kk": "Мәтінді тексеру қызметіне кейбір сұраулар орындалмады.", "en": "Some text review requests failed."},
    "ai.reason.invalid_response": {"ru": "Часть ответов сервиса не прошла проверку качества.", "kk": "Қызметтің кейбір жауаптары сапа тексеруінен өтпеді.", "en": "Some service responses failed validation."},
    "ai.reason.disabled": {"ru": "Проверка текста отключена в настройках сервиса.", "kk": "Қызмет баптауларында мәтінді тексеру өшірілген.", "en": "Text review is disabled in service settings."},
    "ai.reason.empty_text": {"ru": "Не найден текст для языкового анализа.", "kk": "Тілдік талдауға мәтін табылмады.", "en": "No text was available for language review."},
    "pdf.diagnostic": {
        "ru": "Диагностический балл по проверенной части. Это не оценка преподавателя.",
        "kk": "Тексерілген бөлік бойынша диагностикалық балл. Бұл оқытушының бағасы емес.",
        "en": "Diagnostic score for the evaluated portion. This is not an academic grade.",
    },
    "pdf.unverified": {
        "ru": "Профиль предварительный: соответствие действующей методичке кафедры не подтверждено.",
        "kk": "Профиль алдын ала берілген: кафедраның қолданыстағы нұсқаулығына сәйкестігі расталмаған.",
        "en": "Provisional preset: compliance with current department guidance is unverified.",
    },
    "pdf.method": {
        "ru": "Расчёт: {version}. Одно нарушение учитывается один раз; повторы не суммируются. Непроверенные категории исключены из максимума. Сумма штрафов ограничена баллами категории.",
        "kk": "Есептеу: {version}. Бір бұзушылық бір рет есептеледі. Тексерілмеген санаттар максимумға кірмейді. Шегерім санат балымен шектеледі.",
        "en": "Method: {version}. Each criterion is charged once. Unevaluated categories are excluded from the maximum. Deductions are capped at the category maximum.",
    },
    "pdf.deductions": {
        "ru": "Расшифровка снижения баллов",
        "kk": "Балл шегерімдерінің түсіндірмесі",
        "en": "Score deductions",
    },
    "pdf.symbols": {
        "ru": "Символы вне шрифта обозначены кодом [U+XXXX].",
        "kk": "Қаріпте жоқ таңбалар [U+XXXX] кодымен белгіленген.",
        "en": "Characters unavailable in the font are shown as [U+XXXX].",
    },
})


MESSAGES.update({
    "location.paragraph": {"ru": "Абзац {n}", "kk": "{n}-абзац", "en": "Paragraph {n}"},
    "score.provisional_short": {"ru": "предварительно", "kk": "алдын ала", "en": "provisional"},
    "status.pending": {"ru": "Ожидает проверки", "kk": "Тексеруді күтуде", "en": "Queued"},
    "status.running": {"ru": "Проверяется", "kk": "Тексерілуде", "en": "In progress"},
    "status.failed": {"ru": "Проверка не завершена", "kk": "Тексеру аяқталмады", "en": "Check failed"},
    "status.completed": {"ru": "Проверка завершена", "kk": "Тексеру аяқталды", "en": "Completed"},
    "location.section": {"ru": "Раздел {n}", "kk": "{n}-бөлім", "en": "Section {n}"},
    "location.fragment": {"ru": "{section}, фрагмент {n}", "kk": "{section}, {n}-үзінді", "en": "{section}, excerpt {n}"},
    "ai.topic_unspecified": {"ru": "Не указана", "kk": "Көрсетілмеген", "en": "Not specified"},
    "score.coverage": {"ru": "проверено {pct}% текста", "kk": "мәтіннің {pct}% тексерілді", "en": "{pct}% of text reviewed"},
    "score.provisional": {
        "ru": "Предварительный результат из 100: проверка выполнена не полностью. Балл рассчитан по доступным категориям; после полной проверки он может измениться.",
        "kk": "100 балдық алдын ала нәтиже: тексеру толық аяқталмаған. Балл тексерілген санаттар бойынша есептелді; толық тексеруден кейін өзгеруі мүмкін.",
        "en": "Provisional result out of 100: review is incomplete. The score uses available categories and may change after a full review.",
    },
    "score.complete": {"ru": "Все пять категорий проверены. Максимум — 100 баллов.", "kk": "Бес санаттың барлығы тексерілді. Ең жоғары балл — 100.", "en": "All five categories reviewed. Maximum: 100 points."},
    "severity.critical": {"ru": "Критично", "kk": "Маңызды", "en": "Critical"},
    "severity.error": {"ru": "Ошибка", "kk": "Қате", "en": "Error"},
    "severity.warning": {"ru": "Замечание", "kk": "Ескерту", "en": "Warning"},
    "severity.info": {"ru": "Рекомендация", "kk": "Ұсыныс", "en": "Advice"},
    "severity.pass": {"ru": "Соответствует", "kk": "Сәйкес", "en": "Passed"},
    "pdf.method": {
        "ru": "Повтор одного нарушения не увеличивает штраф. Удержания ограничены весом категории. Итог: сумма набранных баллов, делённая на максимум доступных категорий и умноженная на 100.",
        "kk": "Қайталанған бұзушылық үшін балл қайта шегерілмейді. Шегерім санат салмағымен шектеледі. Нәтиже: жиналған балл тексерілген санаттардың максимумына бөлініп, 100-ге көбейтіледі.",
        "en": "Repeated observations are charged once. Deductions are capped by category weight. Total: earned points divided by available category weights, multiplied by 100.",
    },
})


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Look up `key` in the given language, falling back to Russian and
    then to the raw key if nothing is found (never raises — a missing
    translation should degrade gracefully, not crash a check)."""
    lang = (lang or DEFAULT_LANG).lower()
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or next(iter(entry.values()))
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def normalize_lang(value: str | None) -> str:
    value = (value or DEFAULT_LANG).lower()
    return value if value in SUPPORTED_LANGS else DEFAULT_LANG
