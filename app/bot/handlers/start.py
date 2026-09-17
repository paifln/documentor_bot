from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.language import language_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.selection import work_type_keyboard
from app.bot.states import CB, CheckFlowStates
from app.database.models.user import User
from app.database.repositories.user_repository import UserRepository
from app.i18n import normalize_lang, t
from app.rules.presets.loader import get_preset_registry

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User) -> None:
    await state.clear()
    if not db_user.language:
        await message.answer(t("choose_language", "ru"), reply_markup=language_keyboard())
        return
    lang = db_user.language
    await message.answer(t("welcome", lang), reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data.startswith(f"{CB.LANGUAGE}:"))
async def set_language(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    lang = normalize_lang(callback.data.split(":", 1)[1])
    await UserRepository(session).set_language(db_user, lang)
    await session.commit()

    await callback.message.edit_text(t("language_set", lang))
    await callback.message.answer(t("welcome", lang), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == CB.LANGUAGE_MENU)
async def open_language_menu(callback: CallbackQuery, db_user: User) -> None:
    lang = db_user.language or "ru"
    await callback.message.answer(t("choose_language", lang), reply_markup=language_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB.MAIN_MENU)
async def show_main_menu(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    await state.clear()
    lang = db_user.language or "ru"
    await callback.message.edit_text(t("welcome", lang), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == CB.HELP)
async def show_help(callback: CallbackQuery, db_user: User) -> None:
    lang = db_user.language or "ru"
    await callback.message.answer(t("help", lang))
    await callback.answer()


@router.callback_query(F.data == CB.CHECK_NEW)
async def start_check_flow(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    lang = db_user.language or "ru"
    # Documentor serves a single institution (Makhambet University) — no
    # institution picker is needed, we go straight to work-type selection.
    await state.update_data(institution="Makhambet University")
    await _ask_work_type(callback, state, "Makhambet University", lang)


_WORK_TYPE_ORDER = ["coursework", "diploma", "report", "essay"]


async def _ask_work_type(callback: CallbackQuery, state: FSMContext, institution: str, lang: str) -> None:
    registry = get_preset_registry()
    presets = registry.list_for_institution(institution)
    work_types = sorted(
        {p.work_type.value for p in presets},
        key=lambda wt: _WORK_TYPE_ORDER.index(wt) if wt in _WORK_TYPE_ORDER else 99,
    )

    if not work_types:
        await callback.message.answer(t("no_presets_configured", lang))
        await callback.answer()
        return

    await state.set_state(CheckFlowStates.choosing_work_type)
    await callback.message.edit_text(t("ask_work_type", lang), reply_markup=work_type_keyboard(work_types, lang))
    await callback.answer()


@router.callback_query(CheckFlowStates.choosing_work_type, F.data.startswith(f"{CB.WORK_TYPE}:"))
async def choose_work_type(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    lang = db_user.language or "ru"
    work_type = callback.data.split(":", 1)[1]
    data = await state.update_data(work_type=work_type)

    registry = get_preset_registry()
    matches = [
        p for p in registry.list_for_institution(data["institution"]) if p.work_type.value == work_type
    ]
    if not matches:
        await callback.message.answer(t("error.preset_not_found", lang))
        await callback.answer()
        return

    preset = matches[0]
    await state.update_data(preset_id=preset.id)
    await state.set_state(CheckFlowStates.waiting_for_document)
    await callback.message.edit_text(t("work_type_chosen", lang, preset_name=preset.name))
    await callback.answer()
