from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CheckFlowStates(StatesGroup):
    choosing_institution = State()
    choosing_work_type = State()
    waiting_for_document = State()
