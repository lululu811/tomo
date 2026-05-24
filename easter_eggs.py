"""Easter egg detection system for Tomo.

Scans git history and code patterns to trigger fun pet reactions.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tomo.species_manager import get_species


@dataclass
class EasterEggTrigger:
    """A detected easter egg trigger."""

    trigger_type: str
    message: str
    detail: str | None = None


# Commit message keywords and their reactions
COMMIT_KEYWORDS = {
    r"fix\s*(bug|issue|#\d+)": [
        "又修了一个bug？bug见你就跑！",
        "修bug的速度比写bug还快，这很程序员！",
        "bug克星上线！今天第几个了？",
    ],
    r"refactor": [
        "重构一时爽，一直重构一直爽！",
        "祖传代码被你重构了？勇士！",
        "重构是程序员的浪漫，我懂。",
    ],
    r"wip|work.in.progress": [
        "WIP...又在挖坑了是吧？",
        " work in progress = 进度条卡在99%",
        "别急，WIP是程序员的常态。",
    ],
    r"lgtm|looks?\s*good": [
        "LGTM！最有分量的两个字母。",
        "看起来不错？那就是真的不错！",
        "LGTM = Let's Get This Merged!",
    ],
    r"hack|temporary|temp": [
        " temporary = 永久存在的另一种说法...",
        "又写hack了？没事，反正半年后就是你来维护。",
        "这就是传说中的'临时解决方案'吗？（狗头）",
    ],
}

# Code pattern keywords
CODE_PATTERNS = {
    r"TODO": [
        "TODO +1，你的待办事项比我吃的饭还多。",
        "TODO清单又长了...别忘了回头填坑啊！",
        "写了TODO就算做了...吗？",
    ],
    r"FIXME": [
        "FIXME！这代码在向你求救呢。",
        "Fix me later = 永远不会fix",
        "看到FIXME我就想起我的bug清单...",
    ],
    r"HACK|XXX|BUG": [
        "HACK detected！这就是传说中的'优雅'代码吗？",
        "XXX注释...这代码是不是有点少儿不宜？",
        "留下这种注释，你确定未来你不会想删了自己？",
    ],
}

# Late night work messages
LATE_NIGHT_MESSAGES = [
    "凌晨还在commit？你是要修仙吗？",
    "深夜coding，bug陪你到天亮。",
    "这个点还在工作...快去睡觉！代码不会跑的！",
    "夜猫子模式 detected。记得明天补觉。",
]

# Mass deletion messages
MASS_DELETE_MESSAGES = [
    "删了这么多行？是在重构还是在发泄？",
    "代码删得比写得快，这很敏捷开发。",
    "删代码也是一种艺术，你做到了。",
]


def _get_recent_commits(count: int = 5) -> list[dict[str, Any]]:
    """Get recent git commits with metadata."""
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{count}",
                "--pretty=format:%H|%s|%ci",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=".",
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append(
                    {
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                    }
                )
        return commits
    except Exception:
        return []


def _get_commit_diff_stats(commit_hash: str) -> dict[str, int]:
    """Get insertions/deletions for a commit."""
    try:
        result = subprocess.run(
            ["git", "show", "--stat", "--format=", commit_hash],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return {"insertions": 0, "deletions": 0}

        text = result.stdout
        # Look for "1 file changed, 10 insertions(+), 5 deletions(-)"
        match = re.search(r"(\d+)\s+insertion.*?\((\+*)\).*?(\d+)\s+deletion.*?\((\-*)", text)
        if match:
            return {
                "insertions": int(match.group(1)),
                "deletions": int(match.group(3)),
            }
        return {"insertions": 0, "deletions": 0}
    except Exception:
        return {"insertions": 0, "deletions": 0}


def _scan_code_patterns() -> list[str]:
    """Scan git diff for TODO/FIXME/HACK patterns."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "--cached", "-G", "TODO|FIXME|HACK|XXX"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        found = []
        for pattern_name in CODE_PATTERNS:
            if re.search(pattern_name, result.stdout, re.IGNORECASE):
                found.append(pattern_name)
        return found
    except Exception:
        return []


def check_easter_eggs(species: str = "fox") -> list[EasterEggTrigger]:
    """Check for easter egg triggers and return reactions.

    Args:
        species: Pet species for species-specific messages.

    Returns:
        List of triggered easter eggs (empty if none).
    """
    triggers: list[EasterEggTrigger] = []
    species_template = get_species(species)

    # 1. Check recent commits
    commits = _get_recent_commits(3)
    checked_hashes: set[str] = set()

    for commit in commits:
        msg = commit["message"].lower()
        commit_hash = commit["hash"]

        # Skip if we've already checked this commit
        if commit_hash in checked_hashes:
            continue
        checked_hashes.add(commit_hash)

        # Check commit message keywords
        for pattern, messages in COMMIT_KEYWORDS.items():
            if re.search(pattern, msg, re.IGNORECASE):
                triggers.append(
                    EasterEggTrigger(
                        trigger_type="commit_keyword",
                        message=_pick_message(messages, species_template),
                        detail=f"commit: {commit['message'][:50]}",
                    )
                )
                break  # One trigger per commit

        # Check diff stats for mass deletion
        stats = _get_commit_diff_stats(commit_hash)
        if stats["deletions"] > stats["insertions"] * 3 and stats["deletions"] > 50:
            triggers.append(
                EasterEggTrigger(
                    trigger_type="mass_delete",
                    message=_pick_message(MASS_DELETE_MESSAGES, species_template),
                    detail=f"-{stats['deletions']} lines",
                )
            )

        # Check late night commit (23:00 - 05:00)
        try:
            commit_dt = datetime.strptime(commit["date"][:19], "%Y-%m-%d %H:%M:%S")
            hour = commit_dt.hour
            if hour >= 23 or hour < 5:
                triggers.append(
                    EasterEggTrigger(
                        trigger_type="late_night",
                        message=_pick_message(LATE_NIGHT_MESSAGES, species_template),
                        detail=f"commit at {commit_dt.strftime('%H:%M')}",
                    )
                )
        except ValueError:
            pass

    # 2. Scan code patterns in diff
    code_patterns = _scan_code_patterns()
    for pattern in code_patterns:
        messages = CODE_PATTERNS.get(pattern)
        if messages:
            triggers.append(
                EasterEggTrigger(
                    trigger_type="code_pattern",
                    message=_pick_message(messages, species_template),
                    detail=f"pattern: {pattern}",
                )
            )

    return triggers


def _pick_message(messages: list[str], species_template: Any) -> str:
    """Pick a message, optionally using species-specific override."""
    import random

    # Try species-specific dialogue for easter eggs
    species_dialogue = species_template.dialogue.get("easter_egg", [])
    if species_dialogue and random.random() < 0.3:
        return random.choice(species_dialogue)

    return random.choice(messages)
