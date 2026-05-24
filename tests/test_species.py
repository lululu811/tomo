"""Tests for the species system."""

from unittest.mock import patch

from tomo.cli import main
from tomo.species_manager import (
    get_species,
    list_available_species,
)


class TestSpeciesManager:
    def test_list_available_species(self):
        species = list_available_species()
        assert "fox" in species
        assert "cat" in species
        assert "dragon" in species

    def test_get_species_fox(self):
        template = get_species("fox")
        assert template.name == "fox"
        assert "fox" in template.description.lower() or "companion" in template.description.lower()
        assert "egg" in template.stages
        assert "adult" in template.stages

    def test_get_species_cat(self):
        template = get_species("cat")
        assert template.name == "cat"
        assert "cat" in template.description.lower()
        assert len(template.stages) == 5

    def test_get_species_dragon(self):
        template = get_species("dragon")
        assert template.name == "dragon"
        assert "dragon" in template.description.lower()

    def test_get_species_invalid_fallback(self):
        template = get_species("nonexistent")
        # Falls back to default species (fox)
        assert template.species == "fox"
        assert template._data

    def test_get_species_none_fallback(self):
        template = get_species(None)
        assert template.species == "fox"

    def test_stage_art(self):
        template = get_species("cat")
        art = template.get_stage_art("adult")
        assert art is not None
        assert len(art) > 0

    def test_dialogue(self):
        template = get_species("cat")
        greetings = template.get_dialogue("greeting")
        assert len(greetings) > 0


class TestSpeciesCLI:
    def test_species_list(self, runner):
        result = runner.invoke(main, ["species", "--list"])
        assert result.exit_code == 0
        assert "fox" in result.output
        assert "cat" in result.output
        assert "dragon" in result.output

    def test_species_show_current(self, runner, mock_init):
        result = runner.invoke(main, ["species"])
        assert result.exit_code == 0
        assert "Current species" in result.output

    def test_species_switch(self, runner, mock_init, tmp_path):
        from tomo.config import Config
        with patch("tomo.cli._config_path", return_value=tmp_path / "config.yaml"):
            with patch("tomo.cli._db_path", return_value=tmp_path / "tomo.db"):
                with patch("tomo.cli.load_config") as mock_load:
                    # Return a real Config so _data and yaml.dump work
                    mock_load.return_value = Config({"pet": {"name": "Test", "species": "fox"}})
                    # Create a minimal config file and db
                    import yaml
                    cfg = {"pet": {"name": "Test", "species": "fox"}}
                    (tmp_path / "config.yaml").write_text(yaml.dump(cfg))
                    (tmp_path / "tomo.db").touch()

                    result = runner.invoke(main, ["species", "--switch", "cat"])
                    assert result.exit_code == 0
                    assert "cat" in result.output

    def test_species_switch_invalid(self, runner, mock_init):
        result = runner.invoke(main, ["species", "--switch", "unicorn"])
        assert result.exit_code == 0
        assert "Unknown" in result.output
