"""Pet engine growth logic for Tomo."""

from math import log
from typing import Any

from tomo.detector import SessionSnapshot
from tomo.exceptions import ValidationError

EXP_BASE = 100
EXP_GROWTH_FACTOR = 1.5
EXP_PER_CALL = 1
EXP_PER_SKILL = 5
ENERGY_MAX = 100
SATIATION_MAX = 100

MOOD_THRESHOLDS = [
    (80, 80, "energetic"),
    (60, 60, "happy"),
    (40, 40, "neutral"),
    (20, 20, "tired"),
    (0, 0, "exhausted"),
]


class PetEngine:
    """Manages pet growth, energy, satiation, and mood."""

    def __init__(
        self,
        exp: int = 0,
        energy: int = 100,
        satiation: int = 100,
        total_sessions: int = 0,
        total_calls: int = 0,
    ):
        self.exp = max(0, exp)
        self.energy = max(0, min(ENERGY_MAX, energy))
        self.satiation = max(0, min(SATIATION_MAX, satiation))
        self.total_sessions = max(0, total_sessions)
        self.total_calls = max(0, total_calls)

    @property
    def level(self) -> int:
        """Logarithmic level based on total experience."""
        if self.exp <= 0:
            return 1
        return int(log(self.exp / EXP_BASE + 1) / log(EXP_GROWTH_FACTOR)) + 1

    @property
    def mood(self) -> str:
        """Mood derived from energy and satiation thresholds."""
        minimum = min(self.energy, self.satiation)
        for energy_thresh, satiation_thresh, label in MOOD_THRESHOLDS:
            if minimum >= energy_thresh and minimum >= satiation_thresh:
                return label
        return "exhausted"

    @property
    def exp_to_next_level(self) -> int:
        """Experience needed to reach the next level."""
        current_level = self.level
        # Inverse of level formula: exp = EXP_BASE * (EXP_GROWTH_FACTOR ** (level - 1) - 1)
        total_for_next = int(EXP_BASE * (EXP_GROWTH_FACTOR**current_level - 1))
        return max(0, total_for_next - self.exp)

    @property
    def level_progress(self) -> float:
        """Progress toward next level as a float 0.0-1.0."""
        current_level = self.level
        # Exp at the start of current level
        total_for_current = int(EXP_BASE * (EXP_GROWTH_FACTOR ** (current_level - 1) - 1))
        total_for_next = int(EXP_BASE * (EXP_GROWTH_FACTOR**current_level - 1))
        needed = total_for_next - total_for_current
        if needed <= 0:
            return 0.0
        have = self.exp - total_for_current
        return min(1.0, max(0.0, have / needed))

    def add_exp(self, amount: int) -> int:
        """Add experience and return number of levels gained."""
        old_level = self.level
        self.exp += amount
        return self.level - old_level

    def add_exp_from_session(self, snapshot: SessionSnapshot) -> int:
        """Calculate exp from a session snapshot and add it."""
        exp = snapshot.total_calls * EXP_PER_CALL + snapshot.skill_calls * EXP_PER_SKILL
        self.total_sessions += snapshot.session_count
        self.total_calls += snapshot.total_calls
        return self.add_exp(exp)

    def _validate_amount(self, amount: int) -> int:
        """Validate amount is non-negative."""
        if amount < 0:
            raise ValidationError(
                f"Amount must be non-negative, got {amount}",
                details={"amount": amount},
            )
        return amount

    def consume_energy(self, amount: int) -> None:
        """Decrease energy."""
        self._validate_amount(amount)
        self.energy = max(0, self.energy - amount)

    def feed(self, amount: int = 10) -> None:
        """Increase satiation, capped at maximum."""
        self._validate_amount(amount)
        self.satiation = min(SATIATION_MAX, self.satiation + amount)

    def rest(self, amount: int = 20) -> None:
        """Increase energy, capped at maximum."""
        self._validate_amount(amount)
        self.energy = min(ENERGY_MAX, self.energy + amount)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the pet state."""
        return {
            "level": self.level,
            "exp": self.exp,
            "energy": self.energy,
            "satiation": self.satiation,
            "mood": self.mood,
            "total_sessions": self.total_sessions,
            "total_calls": self.total_calls,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PetEngine":
        """Create a PetEngine instance from a dictionary."""
        return cls(
            exp=int(data.get("exp", 0)),
            energy=int(data.get("energy", 100)),
            satiation=int(data.get("satiation", 100)),
            total_sessions=int(data.get("total_sessions", 0)),
            total_calls=int(data.get("total_calls", 0)),
        )
