"""Background daemon for Tomo."""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tomo.achievements import AchievementChecker
from tomo.config import Config, load_config
from tomo.db import Database
from tomo.detector import SessionSnapshot, StatsDetector
from tomo.easter_eggs import check_easter_eggs
from tomo.notification import notify
from tomo.pet_engine import PetEngine

logger = logging.getLogger(__name__)

PID_FILE = Path.home() / ".tomo" / "daemon.pid"
DECAY_INTERVALS = 6  # 6 * 300s = 30 minutes
ENERGY_DECAY = 5
SATIATION_DECAY = 3
LONG_WORK_THRESHOLD = 3600  # 1 hour in seconds


def _merge_tool_breakdown(existing: dict[str, Any] | None, delta: dict[str, Any]) -> dict[str, Any]:
    """Merge tool breakdown deltas into existing counts."""
    result = dict(existing) if existing else {}
    for tool, count in delta.items():
        result[tool] = result.get(tool, 0) + count
    return result


def is_running() -> bool:
    """Check if the daemon is currently running."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def get_pid() -> int | None:
    """Return the daemon PID if running, else None."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        return None


def stop_daemon() -> bool:
    """Stop the daemon if running. Returns success."""
    pid = get_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for PID file to be removed (up to 5 seconds)
        for _ in range(25):
            if not PID_FILE.exists():
                return True
            time.sleep(0.2)

        # Force kill if still running
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)

        # Clean up PID file
        with contextlib.suppress(FileNotFoundError):
            PID_FILE.unlink()
        return True
    except OSError:
        # Process already dead, clean up PID file
        with contextlib.suppress(FileNotFoundError):
            PID_FILE.unlink()
        return True


class Daemon:
    """Tomo background daemon."""

    def __init__(self, interval: int = 300) -> None:
        self.interval = interval
        self.running = False
        self.db: Database | None = None
        self.config: Config | None = None
        self.last_snapshot: SessionSnapshot | None = None
        self.decay_counter = 0
        self.continuous_work_start: float | None = None
        self.last_proactive_notify: dict[str, float] = {}
        self.llm_calls = 0
        self.llm_failures = 0

    def run(self) -> None:
        """Main daemon loop."""
        self._setup_signal_handlers()
        self._write_pid()

        tomo_dir = Path.home() / ".tomo"
        self.db = Database(tomo_dir / "tomo.db")
        self.config = load_config(tomo_dir / "config.yaml")

        detector = StatsDetector()
        self.last_snapshot = detector.read_latest()

        logger.info("Daemon started with interval=%ds", self.interval)

        try:
            while self.running:
                self._sync(detector)
                time.sleep(self.interval)
        finally:
            self._remove_pid()
            logger.info("Daemon stopped")

    def _sync(self, detector: StatsDetector) -> None:
        """Single sync iteration."""
        current = detector.read_latest()
        delta = detector.get_delta(self.last_snapshot)

        assert self.db is not None
        pet = PetEngine.from_dict(self.db.get_all_pet_state())

        # Experience and activity sync
        if delta.total_calls > 0 or delta.session_count > 0:
            levels_gained = pet.add_exp_from_session(delta)

            # Achievement check
            checker = AchievementChecker(self.db)
            new_achievements = checker.check(current, pet.level)
            if new_achievements:
                checker.log_unlocked(new_achievements)
                for ach in new_achievements:
                    notify(
                        f"🎉 解锁成就：{ach.name}",
                        ach.description,
                    )

            # Easter egg detection
            if self.config and self._should_proactive_notify("easter_egg", cooldown=1800):
                eggs = check_easter_eggs(self.config.species)
                for egg in eggs[:2]:  # Max 2 eggs per sync
                    notify("🥚 Tomo 发现彩蛋", egg.message)
                    self.db.log_growth_event("easter_egg", f"[{egg.trigger_type}] {egg.message}")

            # Log growth event
            exp_gained = delta.total_calls + delta.skill_calls * 5
            level_text = f"+{levels_gained}" if levels_gained else "unchanged"
            self.db.log_growth_event(
                "sync",
                f"Synced {delta.session_count} sessions, {delta.total_calls} calls. "
                f"Exp +{exp_gained}. Level {level_text}.",
            )

            # Infer work type via LLM (Skill-based, no hardcoded keywords)
            inferred_type = self._infer_work_type(delta)

            # Update daily stats (includes LLM call tracking)
            self._update_daily_stats(delta, detected_type=inferred_type)

            # Long work detection
            if self.continuous_work_start is None:
                self.continuous_work_start = time.time()
            elif time.time() - self.continuous_work_start > LONG_WORK_THRESHOLD:
                assert self.config is not None
                notify(
                    "🦊 Tomo 提醒",
                    f"{self.config.pet_name} 觉得你工作很久了，休息一下吧！",
                )
                self.continuous_work_start = time.time()  # Reset

            # Proactive feedback: abnormal work patterns
            self._check_proactive_feedback(delta, pet)
        else:
            self.continuous_work_start = None

        # Natural decay every 30 minutes (6 intervals of 300s)
        self.decay_counter += 1
        if self.decay_counter >= DECAY_INTERVALS:
            self.decay_counter = 0
            old_energy = pet.energy
            old_satiation = pet.satiation
            pet.consume_energy(ENERGY_DECAY)
            pet.satiation = max(0, pet.satiation - SATIATION_DECAY)

            self.db.set_pet_state("energy", str(pet.energy))
            self.db.set_pet_state("satiation", str(pet.satiation))

            if old_energy >= 20 and pet.energy < 20:
                assert self.config is not None
                notify(
                    "⚠️ Tomo 能量不足",
                    f"{self.config.pet_name} 快没能量了，给它休息一下吧！",
                )
            if old_satiation >= 20 and pet.satiation < 20:
                assert self.config is not None
                notify(
                    "🍖 Tomo 饿了",
                    f"{self.config.pet_name} 肚子咕咕叫，喂它吃点东西吧！",
                )

        # Save pet state
        self.db.set_pet_state("exp", str(pet.exp))
        self.db.set_pet_state("energy", str(pet.energy))
        self.db.set_pet_state("satiation", str(pet.satiation))
        self.db.set_pet_state("total_sessions", str(pet.total_sessions))
        self.db.set_pet_state("total_calls", str(pet.total_calls))

        self.last_snapshot = current

    def _update_daily_stats(self, delta: SessionSnapshot, detected_type: str | None = None) -> None:
        """Accumulate delta into today's daily_stats record."""
        assert self.db is not None
        today = datetime.now().strftime("%Y-%m-%d")
        existing = self.db.get_daily_stats(today)

        if existing:
            new_session_count = existing.get("session_count", 0) + delta.session_count
            new_total_calls = existing.get("total_calls", 0) + delta.total_calls
            new_skill_calls = existing.get("skill_calls", 0) + delta.skill_calls
            existing_breakdown: dict[str, Any] = {}
            if existing.get("tool_breakdown"):
                with contextlib.suppress(json.JSONDecodeError):
                    existing_breakdown = json.loads(existing["tool_breakdown"])
            new_tool_breakdown = _merge_tool_breakdown(existing_breakdown, delta.tool_breakdown)
            new_llm_calls = existing.get("llm_calls", 0) + self.llm_calls
            new_llm_failures = existing.get("llm_failures", 0) + self.llm_failures
        else:
            new_session_count = delta.session_count
            new_total_calls = delta.total_calls
            new_skill_calls = delta.skill_calls
            new_tool_breakdown = dict(delta.tool_breakdown)
            new_llm_calls = self.llm_calls
            new_llm_failures = self.llm_failures

        self.db.upsert_daily_stats(
            date=today,
            session_count=new_session_count,
            total_calls=new_total_calls,
            skill_calls=new_skill_calls,
            tool_breakdown=new_tool_breakdown,
            detected_type=detected_type,
            llm_calls=new_llm_calls,
            llm_failures=new_llm_failures,
        )

        # Reset counters after sync
        self.llm_calls = 0
        self.llm_failures = 0

    def _setup_signal_handlers(self) -> None:
        self.running = True

        def handle_signal(signum: int, _frame: Any) -> None:
            if signum == signal.SIGHUP:
                logger.info("Received SIGHUP, reloading config...")
                self._reload_config()
                return
            logger.info("Received signal %d, shutting down...", signum)
            self.running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGHUP, handle_signal)

    def _reload_config(self) -> None:
        """Reload configuration without restarting daemon."""
        try:
            tomo_dir = Path.home() / ".tomo"
            self.config = load_config(tomo_dir / "config.yaml")
            logger.info("Config reloaded successfully")
        except Exception as exc:
            logger.warning("Failed to reload config: %s", exc)

    def _write_pid(self) -> None:
        PID_FILE.write_text(str(os.getpid()))

    def _remove_pid(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            PID_FILE.unlink()

    # ------------------------------------------------------------------ #
    # Proactive feedback
    # ------------------------------------------------------------------ #

    def _check_proactive_feedback(self, delta: SessionSnapshot, pet: PetEngine) -> None:
        """Check for abnormal work patterns and send proactive suggestions."""
        if delta.total_calls <= 0:
            return

        # Single-tool concentration (e.g., only Bash for a while)
        if delta.tool_breakdown and len(delta.tool_breakdown) == 1:
            tool_name = list(delta.tool_breakdown.keys())[0]
            if self._should_proactive_notify("single_tool", tool_name):
                suggestion = self._generate_proactive_suggestion(
                    f"你一直在用 {tool_name}，是不是遇到难题了？",
                    pet,
                )
                if suggestion:
                    notify("🦊 Tomo 想说", suggestion)

        # Late night work (23:00 - 05:00)
        hour = datetime.now().hour
        if (hour >= 23 or hour < 5) and self._should_proactive_notify("late_night"):
            suggestion = self._generate_proactive_suggestion(
                "已经很晚了，你还在工作",
                pet,
            )
            if suggestion:
                notify("🌙 Tomo 心疼你", suggestion)

    def _should_proactive_notify(
        self, event_type: str, detail: str | None = None, cooldown: int = 3600
    ) -> bool:
        """Check if enough time has passed since last notification of this type."""
        now = time.time()

        key = f"{event_type}:{detail}" if detail else event_type
        last = self.last_proactive_notify.get(key, 0)
        if now - last < cooldown:
            return False

        self.last_proactive_notify[key] = now
        return True

    def _generate_proactive_suggestion(self, context: str, pet: PetEngine) -> str | None:
        """Generate a proactive suggestion via LLM."""
        assert self.config is not None
        if not self.config.llm_important_only:
            return None
        try:
            from tomo.llm import LLMClient

            client = LLMClient(self.config)
            prompt = (
                f"你是 {self.config.pet_name}，"
                f"{self.config.personality.get('description', '一只小狐狸')}。"
                f"当前状态：{pet.mood}，等级 lv.{pet.level}。"
                f"你发现：{context}。"
                f"请用一句话（不超过30字）温柔地关心用户或给出建议。不要提问。"
            )
            result = client.generate(prompt)
            self.llm_calls += 1
            return result
        except Exception:
            self.llm_failures += 1
            return None

    def _infer_work_type(self, delta: SessionSnapshot) -> str | None:
        """Infer work type from tool usage via LLM (Skill-based, no hardcoded keywords)."""
        if delta.total_calls < 5:
            return None

        assert self.db is not None
        today = datetime.now().strftime("%Y-%m-%d")
        existing = self.db.get_daily_stats(today)
        if existing and existing.get("detected_type"):
            return None  # Already inferred today

        # Build tool usage summary
        tools = sorted(delta.tool_breakdown.items(), key=lambda x: x[1], reverse=True)
        if not tools:
            return None

        tools_desc = "\n".join(f"- {tool}: {count} 次" for tool, count in tools[:8])
        prompt = (
            "根据以下工具使用记录，推断用户正在进行的工作类型。"
            "只输出一个简洁的中文工作类型名称（不超过10个字），不要解释。\n\n"
            f"工具使用情况：\n{tools_desc}\n\n"
            "工作类型："
        )

        assert self.config is not None
        try:
            from tomo.llm import LLMClient

            client = LLMClient(self.config)
            result = client.generate(prompt)
            result = result.strip().strip('"').strip("'")
            if len(result) > 20:
                result = result[:20]
            self.llm_calls += 1
            return result if result else None
        except Exception:
            self.llm_failures += 1
            return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Tomo background daemon")
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()

    # Configure logging with rotation (10MB max, keep 3 backups)
    tomo_dir = Path.home() / ".tomo"
    tomo_dir.mkdir(parents=True, exist_ok=True)
    log_path = tomo_dir / "daemon.log"

    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Also redirect stdout/stderr for uncaptured prints
    log_file = handler.stream
    sys.stdout = log_file
    sys.stderr = log_file

    daemon = Daemon(interval=args.interval)
    daemon.run()


if __name__ == "__main__":
    main()
