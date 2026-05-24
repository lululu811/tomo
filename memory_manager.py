"""Memory and affinity management for Tomo.

- Memory: persistent key-value store for facts, preferences, and extracted insights.
- Affinity: intimacy score that grows with interactions, unlocking titles and behaviors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from tomo.db import Database

# Affinity thresholds and titles
AFFINITY_TITLES = [
    (0, "陌生人"),
    (10, "认识"),
    (50, "朋友"),
    (150, "搭档"),
    (300, "知己"),
    (500, "灵魂伴侣"),
]

# Affinity gains per interaction type
AFFINITY_GAINS = {
    "chat": 1,
    "feed": 2,
    "rest": 1,
    "play": 3,
    "remember": 2,
    "achievement": 5,
}

# Auto-extraction patterns from chat
EXTRACTION_PATTERNS = {
    "deadline": re.compile(
        r"(明天|后天|下周|这周|\d+号).*?(发布|上线|截止|deadline|due)", re.IGNORECASE
    ),
    "preference": re.compile(r"(我讨厌|我不喜欢|我喜欢|我爱|我最爱).*?", re.IGNORECASE),
    "goal": re.compile(r"(我要|我想|我打算|我计划).*?(做|写|学|完成)", re.IGNORECASE),
    "stress": re.compile(r"(好累|好烦|压力|焦虑|抑郁|想辞职|想躺平)", re.IGNORECASE),
    "tech": re.compile(
        r"(在用|学了|刚学|刚开始用).*?(React|Vue|Python|Go|Rust|TypeScript|Java|Kotlin|Swift|Flutter)",
        re.IGNORECASE,
    ),
}


@dataclass
class AffinityLevel:
    """Represents the current affinity level."""

    score: int
    title: str
    next_title: str | None
    progress: float  # 0.0 to 1.0 toward next level


class MemoryManager:
    """Manages pet memories and user affinity."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ #
    # Affinity
    # ------------------------------------------------------------------ #

    def get_affinity(self) -> int:
        """Get current affinity score."""
        raw = self.db.get_pet_state("affinity")
        return int(raw) if raw else 0

    def add_affinity(self, interaction_type: str) -> AffinityLevel:
        """Add affinity from an interaction and return new level info."""
        gain = AFFINITY_GAINS.get(interaction_type, 1)
        current = self.get_affinity()
        new_score = current + gain
        self.db.set_pet_state("affinity", str(new_score))
        return self._get_affinity_level(new_score)

    def _get_affinity_level(self, score: int) -> AffinityLevel:
        """Calculate affinity level from score."""
        current_title = AFFINITY_TITLES[0][1]
        next_title = None
        next_threshold = None

        for threshold, title in AFFINITY_TITLES:
            if score >= threshold:
                current_title = title
            else:
                next_title = title
                next_threshold = threshold
                break

        if next_threshold is None:
            progress = 1.0
        else:
            # Find previous threshold
            prev_threshold = 0
            for t, _ in AFFINITY_TITLES:
                if t <= score:
                    prev_threshold = t
            progress = min(1.0, (score - prev_threshold) / (next_threshold - prev_threshold))

        return AffinityLevel(
            score=score,
            title=current_title,
            next_title=next_title,
            progress=progress,
        )

    def get_affinity_display(self) -> str:
        """Get a human-readable affinity display."""
        level = self._get_affinity_level(self.get_affinity())
        if level.next_title:
            bar_length = 10
            filled = int(level.progress * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            return f"亲密度: {level.title} {bar} ({level.score}) → {level.next_title}"
        return f"亲密度: {level.title} (MAX)"

    # ------------------------------------------------------------------ #
    # Memory CRUD
    # ------------------------------------------------------------------ #

    def remember(
        self,
        key: str,
        value: str,
        category: str = "fact",
        importance: int = 1,
    ) -> None:
        """Store a memory. Auto-normalizes key."""
        key = key.strip().lower()
        self.db.set_memory(key, value, category, importance)

    def recall(self, key: str) -> str | None:
        """Retrieve a memory value by key."""
        mem = self.db.get_memory(key)
        return mem["value"] if mem else None

    def forget(self, key: str) -> bool:
        """Delete a memory by key."""
        return self.db.delete_memory(key.strip().lower())

    def list_memories(
        self,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List memories."""
        return self.db.get_memories(category=category, limit=limit)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories."""
        return self.db.search_memories(query, limit)

    def clear(self, category: str | None = None) -> None:
        """Clear memories."""
        self.db.clear_memories(category)

    # ------------------------------------------------------------------ #
    # Auto-extraction from chat
    # ------------------------------------------------------------------ #

    def extract_from_message(self, message: str) -> list[tuple[str, str, str]]:
        """Extract potential memories from a user message.

        Returns list of (category, key, value) tuples.
        """
        extracted: list[tuple[str, str, str]] = []
        for category, pattern in EXTRACTION_PATTERNS.items():
            match = pattern.search(message)
            if match:
                key = match.group(0)[:30]  # Truncate for key
                value = match.group(0)
                extracted.append((category, key, value))
        return extracted

    def store_extracted(self, message: str) -> list[str]:
        """Extract and store memories from a message.

        Returns list of stored keys.
        """
        extracted = self.extract_from_message(message)
        stored: list[str] = []
        for category, key, value in extracted:
            # Skip if already exists with same value
            existing = self.db.get_memory(key)
            if existing and existing["value"] == value:
                continue
            self.remember(key, value, category, importance=2)
            stored.append(key)
        return stored

    # ------------------------------------------------------------------ #
    # Memory context for prompts
    # ------------------------------------------------------------------ #

    def get_memory_context(self, limit: int = 5) -> list[str]:
        """Get recent memories formatted for LLM context.

        Returns list of "- 用户说: ..." strings.
        """
        memories = self.db.get_memories(limit=limit)
        lines: list[str] = []
        for mem in memories:
            cat = mem.get("category", "fact")
            val = mem.get("value", "")
            if cat == "deadline":
                lines.append(f"- 用户提到过 deadline: {val}")
            elif cat == "preference":
                lines.append(f"- 用户的喜好: {val}")
            elif cat == "goal":
                lines.append(f"- 用户的目标: {val}")
            elif cat == "stress":
                lines.append(f"- 用户最近状态: {val}")
            elif cat == "tech":
                lines.append(f"- 用户在用的技术: {val}")
            else:
                lines.append(f"- 用户说: {val}")
        return lines
