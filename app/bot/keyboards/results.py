from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB
from app.i18n import t


def results_keyboard(check_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.result_scores", lang),
                    callback_data=f"{CB.RESULT_SCORES}:{check_id}",
                ),
                InlineKeyboardButton(
                    text=t("btn.result_errors", lang),
                    callback_data=f"{CB.RESULT_ERRORS}:{check_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.result_recommendations", lang),
                    callback_data=f"{CB.RESULT_RECOMMENDATIONS}:{check_id}",
                ),
                InlineKeyboardButton(
                    text=t("btn.result_pdf", lang), callback_data=f"{CB.RESULT_PDF}:{check_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("btn.result_new_check", lang), callback_data=CB.RESULT_NEW_CHECK
                )
            ],
        ]
    )
