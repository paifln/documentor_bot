"""Loads RulePreset YAML files from disk.

Adding a new preset = dropping a new .yaml file into rules/presets/ and
restarting the app (or calling reload()) — no Python changes required,
per spec §10/§23.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.common.exceptions import RulePresetNotFoundError
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.rules.models import RulePreset

logger = get_logger(__name__)


class PresetRegistry:
    def __init__(self, presets_dir: Path | None = None):
        settings = get_settings()
        self.presets_dir = presets_dir or settings.presets_dir
        self._cache: dict[str, RulePreset] = {}
        self.reload()

    def reload(self) -> None:
        self._cache.clear()
        if not self.presets_dir.exists():
            logger.warning("presets_dir_missing", path=str(self.presets_dir))
            return
        for file in sorted(self.presets_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
                preset = RulePreset.model_validate(data)
                preset.validate_weights()
                self._cache[preset.id] = preset
            except Exception as exc:  # noqa: BLE001
                logger.error("preset_load_failed", file=str(file), error=str(exc))
        logger.info("presets_loaded", count=len(self._cache), ids=list(self._cache.keys()))

    def get(self, preset_id: str) -> RulePreset:
        preset = self._cache.get(preset_id)
        if preset is None or not preset.is_active:
            raise RulePresetNotFoundError(f"preset '{preset_id}' not found or inactive")
        return preset

    def list_active(self) -> list[RulePreset]:
        return [p for p in self._cache.values() if p.is_active]

    def list_institutions(self) -> list[str]:
        return sorted({p.institution for p in self.list_active()})

    def list_for_institution(self, institution: str) -> list[RulePreset]:
        return [p for p in self.list_active() if p.institution == institution]


_registry: PresetRegistry | None = None


def get_preset_registry() -> PresetRegistry:
    global _registry
    if _registry is None:
        _registry = PresetRegistry()
    return _registry
