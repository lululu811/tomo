"""Claude Code session stats detector for Tomo."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionSnapshot:
    """Aggregated snapshot of Claude Code session stats."""

    session_count: int
    total_calls: int
    skill_calls: int
    tool_breakdown: dict[str, int]
    latest_update: int


class StatsDetector:
    """Reads and aggregates Claude Code session statistics."""

    def __init__(self, stats_path: str | None = None):
        self.stats_path = (
            Path(stats_path) if stats_path else Path.home() / ".claude" / ".session-stats.json"
        )

    def read_latest(self) -> SessionSnapshot:
        """Read the stats file and return an aggregated snapshot."""
        if not self.stats_path.exists():
            logger.debug("Stats file not found: %s", self.stats_path)
            return SessionSnapshot(0, 0, 0, {}, 0)

        try:
            with open(self.stats_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            logger.warning("Corrupted stats file (%s): %s", self.stats_path, exc)
            return SessionSnapshot(0, 0, 0, {}, 0)
        except OSError as exc:
            logger.warning("Cannot read stats file (%s): %s", self.stats_path, exc)
            return SessionSnapshot(0, 0, 0, {}, 0)

        sessions = data.get("sessions", {})
        if not sessions:
            logger.debug("No sessions found in stats file")
            return SessionSnapshot(0, 0, 0, {}, 0)

        session_count = len(sessions)
        total_calls = 0
        skill_calls = 0
        tool_breakdown: dict[str, int] = defaultdict(int)
        latest_update = 0

        for session in sessions.values():
            total_calls += session.get("total_calls", 0)
            latest_update = max(latest_update, session.get("updated_at", 0))

            for tool, count in session.get("tool_counts", {}).items():
                tool_breakdown[tool] += count
                if tool == "Skill":
                    skill_calls += count

        return SessionSnapshot(
            session_count=session_count,
            total_calls=total_calls,
            skill_calls=skill_calls,
            tool_breakdown=dict(tool_breakdown),
            latest_update=latest_update,
        )

    def get_delta(self, previous: SessionSnapshot | None = None) -> SessionSnapshot:
        """Return the delta between current and previous snapshots."""
        current = self.read_latest()
        if previous is None:
            return current

        delta_tools = {}
        all_tools = set(current.tool_breakdown.keys()) | set(previous.tool_breakdown.keys())
        for tool in all_tools:
            delta_tools[tool] = max(
                0, current.tool_breakdown.get(tool, 0) - previous.tool_breakdown.get(tool, 0)
            )

        return SessionSnapshot(
            session_count=max(0, current.session_count - previous.session_count),
            total_calls=max(0, current.total_calls - previous.total_calls),
            skill_calls=max(0, current.skill_calls - previous.skill_calls),
            tool_breakdown=delta_tools,
            latest_update=max(0, current.latest_update - previous.latest_update),
        )
