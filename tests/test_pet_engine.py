"""Tests for the pet engine."""

import pytest

from tomo.detector import SessionSnapshot
from tomo.exceptions import ValidationError
from tomo.pet_engine import PetEngine


class TestPetEngineInit:
    def test_default_init(self, fresh_pet):
        assert fresh_pet.exp == 0
        assert fresh_pet.energy == 100
        assert fresh_pet.satiation == 100
        assert fresh_pet.total_sessions == 0
        assert fresh_pet.total_calls == 0

    def test_custom_init(self):
        pet = PetEngine(exp=50, energy=80, satiation=60, total_sessions=5, total_calls=100)
        assert pet.exp == 50
        assert pet.energy == 80
        assert pet.satiation == 60
        assert pet.total_sessions == 5
        assert pet.total_calls == 100

    def test_negative_values_clamped(self):
        pet = PetEngine(exp=-10, energy=-5, satiation=-3)
        assert pet.exp == 0
        assert pet.energy == 0
        assert pet.satiation == 0

    def test_energy_satiation_capped(self):
        pet = PetEngine(energy=150, satiation=200)
        assert pet.energy == 100
        assert pet.satiation == 100


class TestPetEngineLevel:
    def test_level_1_at_zero_exp(self, fresh_pet):
        assert fresh_pet.level == 1

    def test_level_1_at_low_exp(self):
        pet = PetEngine(exp=10)
        assert pet.level == 1

    def test_level_2(self):
        pet = PetEngine(exp=82)
        assert pet.level >= 2

    def test_level_progress(self):
        pet = PetEngine(exp=0)
        assert pet.level_progress == 0.0

        pet = PetEngine(exp=25)
        assert 0.0 < pet.level_progress < 1.0


class TestPetEngineMood:
    def test_energetic(self):
        pet = PetEngine(energy=85, satiation=85)
        assert pet.mood == "energetic"

    def test_happy(self):
        pet = PetEngine(energy=70, satiation=70)
        assert pet.mood == "happy"

    def test_neutral(self):
        pet = PetEngine(energy=50, satiation=50)
        assert pet.mood == "neutral"

    def test_tired(self):
        pet = PetEngine(energy=25, satiation=25)
        assert pet.mood == "tired"

    def test_exhausted(self):
        pet = PetEngine(energy=10, satiation=10)
        assert pet.mood == "exhausted"

    def test_mood_uses_minimum(self):
        pet = PetEngine(energy=90, satiation=45)
        assert pet.mood == "neutral"


class TestPetEngineExp:
    def test_add_exp(self, fresh_pet):
        levels = fresh_pet.add_exp(100)
        assert levels >= 1
        assert fresh_pet.exp == 100

    def test_add_exp_from_session(self):
        pet = PetEngine()
        snapshot = SessionSnapshot(2, 20, 3, {"Bash": 20}, 0)
        levels = pet.add_exp_from_session(snapshot)
        expected_exp = 20 * 1 + 3 * 5
        assert pet.exp == expected_exp
        assert pet.total_sessions == 2
        assert pet.total_calls == 20

    def test_exp_to_next_level(self, fresh_pet):
        assert fresh_pet.exp_to_next_level > 0


class TestPetEngineEnergy:
    def test_consume_energy(self, fresh_pet):
        fresh_pet.consume_energy(20)
        assert fresh_pet.energy == 80

    def test_consume_energy_capped_at_zero(self, fresh_pet):
        fresh_pet.consume_energy(150)
        assert fresh_pet.energy == 0

    def test_consume_energy_negative_raises(self, fresh_pet):
        with pytest.raises(ValidationError):
            fresh_pet.consume_energy(-5)

    def test_rest(self, fresh_pet):
        fresh_pet.energy = 50
        fresh_pet.rest(30)
        assert fresh_pet.energy == 80

    def test_rest_capped(self, fresh_pet):
        fresh_pet.rest(50)
        assert fresh_pet.energy == 100


class TestPetEngineSatiation:
    def test_feed(self, fresh_pet):
        fresh_pet.satiation = 50
        fresh_pet.feed(30)
        assert fresh_pet.satiation == 80

    def test_feed_capped(self, fresh_pet):
        fresh_pet.feed(50)
        assert fresh_pet.satiation == 100

    def test_feed_negative_raises(self, fresh_pet):
        with pytest.raises(ValidationError):
            fresh_pet.feed(-10)


class TestPetEngineStage:
    def test_stage_egg(self, fresh_pet):
        assert fresh_pet.stage == "egg"

    def test_stage_baby(self):
        pet = PetEngine(exp=10)
        assert pet.stage == "baby"

    def test_stage_child(self):
        pet = PetEngine(exp=50)
        assert pet.stage == "child"

    def test_stage_teen(self):
        pet = PetEngine(exp=150)
        assert pet.stage == "teen"

    def test_stage_adult(self):
        pet = PetEngine(exp=500)
        assert pet.stage == "adult"

    def test_stage_in_to_dict(self, fresh_pet):
        data = fresh_pet.to_dict()
        assert data["stage"] == "egg"


class TestPetEngineSerialization:
    def test_to_dict(self, fresh_pet):
        data = fresh_pet.to_dict()
        assert data["level"] == 1
        assert data["stage"] == "egg"
        assert data["exp"] == 0
        assert data["energy"] == 100
        assert data["satiation"] == 100
        assert data["mood"] == "energetic"

    def test_from_dict(self):
        data = {"exp": "50", "energy": "80", "satiation": "60"}
        pet = PetEngine.from_dict(data)
        assert pet.exp == 50
        assert pet.energy == 80
        assert pet.satiation == 60
        assert pet.stage == "child"
