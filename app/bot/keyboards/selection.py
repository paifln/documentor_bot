from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB
from app.i18n import t

_WORK_TYPE_KEYS = {
    "coursework": "work_type.coursework",
    "diploma": "work_type.diploma",
    "report": "work_type.report",
    "essay": "work_type.essay",
}


def work_type_keyboard(work_types: list[str], lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t(_WORK_TYPE_KEYS.get(wt, wt), lang),
                callback_data=f"{CB.WORK_TYPE}:{wt}",
            )
        ]
        for wt in work_types
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
