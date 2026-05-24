"""Achievement share card generator for Tomo.

Builds beautiful terminal cards using Rich, plus a plain-text ASCII version
for easy copying to social platforms.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rich.align import Align
from rich.box import DOUBLE
from rich.console import Console
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from tomo.achievements import Achievement
    from tomo.config import Config
    from tomo.pet_engine import PetEngine


def _format_unlock_time(unlock_time: str | None) -> str:
    """Format an ISO unlock timestamp for display."""
    if not unlock_time:
        return "刚刚"
    try:
        dt = datetime.fromisoformat(unlock_time)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return unlock_time[:16]


def _get_mood_emoji(mood: str) -> str:
    """Map mood to emoji."""
    return {
        "energetic": "⚡",
        "happy": "😊",
        "neutral": "😐",
        "tired": "😴",
        "exhausted": "💀",
    }.get(mood, "😐")


def build_share_card(
    achievement: Achievement,
    pet: PetEngine,
    config: Config,
    unlock_time: str | None = None,
) -> Table:
    """Build a Rich-renderable achievement share card.

    Returns a Rich Table that can be printed with console.print().
    """
    # Main card table with border
    card = Table(
        box=DOUBLE,
        expand=False,
        show_header=False,
        show_edge=True,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    card.add_column(justify="center")

    # Achievement header: big icon + name
    header = Text.assemble(
        (f"{achievement.icon}  ", "bold bright_yellow"),
        (achievement.name, "bold bright_white"),
        (f"\n{achievement.description}", "italic bright_black"),
    )
    card.add_row(Align.center(header))

    # Divider line
    card.add_row(Text("─" * 40, style="dim"))

    # Pet info row: avatar + stats
    mood_emoji = _get_mood_emoji(pet.mood)
    pet_info = Text.assemble(
        (f"{config.pet_avatar} {config.pet_name}", "bold bright_cyan"),
        (f"  lv.{pet.level}  {mood_emoji}", "bright_white"),
        (f"  {pet.stage}", "dim"),
    )
    card.add_row(Align.center(pet_info))

    # Unlock time
    time_str = _format_unlock_time(unlock_time)
    time_text = Text(f"🏆 解锁于 {time_str}", style="bright_green")
    card.add_row(Align.center(time_text))

    return card


def build_ascii_card(
    achievement: Achievement,
    pet: PetEngine,
    config: Config,
    unlock_time: str | None = None,
) -> str:
    """Build a plain-text ASCII card for easy copying.

    Returns a string suitable for pasting into Twitter, 即刻, etc.
    """
    time_str = _format_unlock_time(unlock_time)
    mood_emoji = _get_mood_emoji(pet.mood)

    lines = [
        "╔" + "═" * 42 + "╗",
        "║" + " " * 42 + "║",
        f"║{achievement.icon}  {achievement.name:^38}║",
        f"║  {achievement.description:^38}║",
        "║" + " " * 42 + "║",
        "║" + "─" * 42 + "║",
        "║" + " " * 42 + "║",
        f"║  {config.pet_avatar} {config.pet_name}"
        f"  lv.{pet.level}  {mood_emoji}"
        f"  {pet.stage:^12}  ║",
        f"║  🏆 解锁于 {time_str:^27}  ║",
        "║" + " " * 42 + "║",
        "╚" + "═" * 42 + "╝",
        "",
        "Powered by Tomo 🦊",
    ]
    return "\n".join(lines)


def build_html_card(
    achievement: Achievement,
    pet: PetEngine,
    config: Config,
    unlock_time: str | None = None,
) -> str:
    """Build an HTML snippet for the achievement card."""
    time_str = _format_unlock_time(unlock_time)
    mood_emoji = _get_mood_emoji(pet.mood)

    # fmt: off
    css = (
        'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", '
        'Roboto, sans-serif; background: #0d1117; color: #c9d1d9; '
        'display: flex; justify-content: center; align-items: center; '
        'min-height: 100vh; margin: 0; }'
        '\n.card { border: 2px solid #8b5cf6; border-radius: 16px; '
        'padding: 32px; max-width: 400px; text-align: center; '
        'background: #161b22; }'
        '\n.icon { font-size: 48px; margin-bottom: 8px; }'
        '\n.name { font-size: 24px; font-weight: bold; color: #f0f6fc; '
        'margin: 8px 0; }'
        '\n.desc { font-size: 14px; color: #8b949e; margin-bottom: 16px; }'
        '\n.divider { border-top: 1px solid #30363d; margin: 16px 0; }'
        '\n.pet { font-size: 16px; color: #58a6ff; margin: 8px 0; }'
        '\n.time { font-size: 13px; color: #3fb950; margin: 8px 0; }'
        '\n.footer { font-size: 11px; color: #484f58; margin-top: 16px; }'
    )
    # fmt: on
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{css}
</style>
</head>
<body>
<div class="card">
<div class="icon">{achievement.icon}</div>
<div class="name">{achievement.name}</div>
<div class="desc">{achievement.description}</div>
<div class="divider"></div>
<div class="pet">{config.pet_avatar} {config.pet_name} lv.{pet.level} {mood_emoji} {pet.stage}</div>
<div class="time">🏆 解锁于 {time_str}</div>
<div class="footer">Powered by Tomo</div>
</div>
</body>
</html>"""


def render_card_to_string(card: Table) -> str:
    """Render a Rich card to a string (for testing or export)."""
    console = Console(force_terminal=True, width=80)
    with console.capture() as capture:
        console.print(card)
    return capture.get()
