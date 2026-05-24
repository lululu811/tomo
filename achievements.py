"""Achievement and milestone system for Tomo."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomo.db import Database
    from tomo.detector import SessionSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Achievement:
    """Represents a single achievement."""

    key: str
    name: str
    description: str
    icon: str


# Achievement definitions
ACHIEVEMENTS: dict[str, Achievement] = {
    "first_meeting": Achievement(
        key="first_meeting",
        name="初次见面",
        description="Tomo 第一次陪伴你工作",
        icon="🌟",
    ),
    "night_owl": Achievement(
        key="night_owl",
        name="夜猫子",
        description="在深夜（23:00 后）坚持工作",
        icon="🌙",
    ),
    "early_bird": Achievement(
        key="early_bird",
        name="早起的鸟儿",
        description="在清晨（6:00 前）开始工作",
        icon="🌅",
    ),
    "tool_master": Achievement(
        key="tool_master",
        name="工具大师",
        description="单会话累计调用工具 50 次以上",
        icon="🛠️",
    ),
    "skill_enthusiast": Achievement(
        key="skill_enthusiast",
        name="Skill 达人",
        description="单次会话使用 Skill 5 次以上",
        icon="🎯",
    ),
    "workaholic": Achievement(
        key="workaholic",
        name="工作狂",
        description="单日会话数达到 5 次",
        icon="💼",
    ),
    "heavy_user": Achievement(
        key="heavy_user",
        name="重度用户",
        description="单日累计调用工具 200 次以上",
        icon="⚡",
    ),
    "multi_talented": Achievement(
        key="multi_talented",
        name="多面手",
        description="累计在 3 种以上不同类型的工作目录中工作过",
        icon="🎭",
    ),
    "level_up_3": Achievement(
        key="level_up_3",
        name="初出茅庐",
        description="Tomo 达到 3 级",
        icon="🥉",
    ),
    "level_up_5": Achievement(
        key="level_up_5",
        name="独当一面",
        description="Tomo 达到 5 级",
        icon="🥈",
    ),
    "level_up_10": Achievement(
        key="level_up_10",
        name="登堂入室",
        description="Tomo 达到 10 级",
        icon="🥇",
    ),
}


class AchievementChecker:
    """Checks session and pet state for newly unlocked achievements."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def _already_unlocked(self, key: str) -> bool:
        """Check if an achievement was already unlocked (fast path via pet_state)."""
        return key in self.db.get_unlocked_achievement_keys()

    def check(self, snapshot: SessionSnapshot, level: int) -> list[Achievement]:
        """Check for newly unlocked achievements and return them."""
        unlocked: list[Achievement] = []
        now = datetime.now()
        hour = now.hour

        # first_meeting
        if snapshot.session_count >= 1:
            ach = ACHIEVEMENTS["first_meeting"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # night_owl: 23:00 - 23:59
        if hour >= 23:
            ach = ACHIEVEMENTS["night_owl"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # early_bird: 05:00 - 05:59
        if 5 <= hour < 6:
            ach = ACHIEVEMENTS["early_bird"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # tool_master
        if snapshot.total_calls >= 50:
            ach = ACHIEVEMENTS["tool_master"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # skill_enthusiast
        if snapshot.skill_calls >= 5:
            ach = ACHIEVEMENTS["skill_enthusiast"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # workaholic - check daily stats
        now.strftime("%Y-%m-%d")
        # We approximate using session_count from snapshot as today's total
        # In a real system we'd query daily_stats table
        if snapshot.session_count >= 5:
            ach = ACHIEVEMENTS["workaholic"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # heavy_user
        if snapshot.total_calls >= 200:
            ach = ACHIEVEMENTS["heavy_user"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        # level_up milestones
        if level >= 3:
            ach = ACHIEVEMENTS["level_up_3"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)
        if level >= 5:
            ach = ACHIEVEMENTS["level_up_5"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)
        if level >= 10:
            ach = ACHIEVEMENTS["level_up_10"]
            if not self._already_unlocked(ach.key):
                unlocked.append(ach)

        return unlocked

    def log_unlocked(self, achievements: list[Achievement]) -> None:
        """Log unlocked achievements to the database."""
        for ach in achievements:
            self.db.log_growth_event(
                event_type="achievement",
                description=f"{ach.icon} 解锁成就：{ach.name} — {ach.description}",
                triggered_by={"achievement_key": ach.key},
            )
            self.db.unlock_achievement(ach.key)
            logger.info("Achievement unlocked: %s", ach.name)

    def get_unlocked_achievements(self, limit: int = 50) -> list[Achievement]:
        """Return list of already unlocked achievements sorted by unlock time (newest first)."""
        keys = self.db.get_unlocked_achievement_keys()
        times = self.db.get_achievement_times()
        # Sort by unlock time descending, then by key for stable ordering
        sorted_keys = sorted(
            keys,
            key=lambda k: (times.get(k, "1970-01-01T00:00:00"), k),
            reverse=True,
        )
        return [ACHIEVEMENTS[k] for k in sorted_keys if k in ACHIEVEMENTS][:limit]
