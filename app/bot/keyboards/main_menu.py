from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB
from app.i18n import t


def main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("menu.check_new", lang), callback_data=CB.CHECK_NEW)],
            [InlineKeyboardButton(text=t("menu.history", lang), callback_data=CB.HISTORY)],
            [InlineKeyboardButton(text=t("menu.settings", lang), callback_data=CB.SETTINGS)],
            [InlineKeyboardButton(text=t("menu.language", lang), callback_data=CB.LANGUAGE_MENU)],
            [InlineKeyboardButton(text=t("menu.help", lang), callback_data=CB.HELP)],
        ]
    )
