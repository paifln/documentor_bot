from __future__ import annotations


class CB:
    """Callback-data string constants. Kept short (Telegram limits callback_data
    to 64 bytes) — dynamic ids are appended after a ':' separator, e.g.
    f"{CB.INSTITUTION}:{institution_name}"."""

    CHECK_NEW = "check_new"
    HISTORY = "history"
    SETTINGS = "settings"
    HELP = "help"
    MAIN_MENU = "main_menu"
    LANGUAGE = "lang"
    LANGUAGE_MENU = "lang_menu"

    INSTITUTION = "inst"
    WORK_TYPE = "wtype"

    RESULT_SCORES = "res_scores"
    RESULT_ERRORS = "res_errors"
    RESULT_RECOMMENDATIONS = "res_recs"
    RESULT_PDF = "res_pdf"
    RESULT_NEW_CHECK = "res_new"

    ADMIN_STATS = "admin_stats"
