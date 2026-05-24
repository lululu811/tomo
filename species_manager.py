"""Species template manager for Tomo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"

DEFAULT_SPECIES = "fox"


def _load_species_template(species: str) -> dict[str, Any]:
    """Load a species template YAML file."""
    template_path = TEMPLATES_DIR / f"{species}.yaml"
    if not template_path.exists():
        return {}
    try:
        return yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


class SpeciesTemplate:
    """Wraps a species template with convenient accessors."""

    def __init__(self, species: str):
        self.species = species
        self._data = _load_species_template(species)

    @property
    def name(self) -> str:
        return self._data.get("name", self.species)

    @property
    def description(self) -> str:
        return self._data.get("description", "A mysterious companion.")

    @property
    def stages(self) -> dict[str, str]:
        return self._data.get("stages", {})

    @property
    def growth_thresholds(self) -> dict[str, int]:
        return self._data.get("growth", {})

    @property
    def dialogue(self) -> dict[str, list[str]]:
        return self._data.get("dialogue", {})

    def get_stage_art(self, stage: str) -> str | None:
        """Return ASCII art for a given evolution stage."""
        art = self.stages.get(stage)
        if art:
            return art.rstrip("\n")
        return None

    def get_dialogue(self, category: str) -> list[str]:
        """Return dialogue lines for a category (greeting, idle, praise, encouragement)."""
        return self.dialogue.get(category, [])


def list_available_species() -> list[str]:
    """Return list of available species names (from template files)."""
    species = []
    if TEMPLATES_DIR.exists():
        for path in TEMPLATES_DIR.glob("*.yaml"):
            species.append(path.stem)
    return sorted(species)


def get_species(species: str | None) -> SpeciesTemplate:
    """Get a species template, falling back to default if not found."""
    if not species:
        species = DEFAULT_SPECIES
    template = SpeciesTemplate(species)
    if not template._data:
        return SpeciesTemplate(DEFAULT_SPECIES)
    return template
