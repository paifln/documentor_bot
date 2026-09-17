from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB

_LANGUAGE_BUTTONS = [
    ("kk", "🇰🇿 Қазақша"),
    ("ru", "🇷🇺 Русский"),
    ("en", "🇬🇧 English"),
]


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{CB.LANGUAGE}:{code}")]
            for code, label in _LANGUAGE_BUTTONS
        ]
    )
