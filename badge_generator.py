"""GitHub Profile Badge SVG generator for Tomo.

Generates an SVG badge showing pet status, coding stats, and affinity.
Supports dark/light theme adaptation via CSS media queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tomo.config import Config
    from tomo.pet_engine import PetEngine


# Badge dimensions
BADGE_WIDTH = 400
BADGE_HEIGHT = 220
PADDING = 16

# Color palettes
COLORS = {
    "bg": {
        "light": "#ffffff",
        "dark": "#0d1117",
    },
    "border": {
        "light": "#d0d7de",
        "dark": "#30363d",
    },
    "text_primary": {
        "light": "#1f2328",
        "dark": "#e6edf3",
    },
    "text_secondary": {
        "light": "#656d76",
        "dark": "#8b949e",
    },
    "accent": {
        "light": "#0969da",
        "dark": "#58a6ff",
    },
    "energy": {
        "light": "#1a7f37",
        "dark": "#3fb950",
    },
    "satiation": {
        "light": "#bc4c00",
        "dark": "#d29922",
    },
    "mood": {
        "light": "#6e7781",
        "dark": "#8b949e",
    },
}


def _bar_svg(
    value: int,
    max_val: int = 100,
    x: int = 0,
    y: int = 0,
    width: int = 120,
    height: int = 6,
    color_key: str = "energy",
) -> str:
    """Generate a horizontal progress bar in SVG."""
    ratio = min(1.0, value / max_val)
    filled_width = int(width * ratio)

    # Use CSS variables for fill color so it adapts to theme
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{height // 2}" fill="var(--tomo-track)" />\n'
        f'<rect x="{x}" y="{y}" width="{filled_width}" height="{height}" '
        f'rx="{height // 2}" fill="var(--tomo-{color_key})" />\n'
    )


def _mood_emoji(mood: str) -> str:
    return {
        "energetic": "⚡",
        "happy": "😊",
        "neutral": "😐",
        "tired": "😴",
        "exhausted": "💀",
    }.get(mood, "😐")


def _stage_label(stage: str) -> str:
    labels = {
        "egg": "蛋",
        "baby": "婴儿",
        "child": "儿童",
        "teen": "少年",
        "adult": "成年",
    }
    return labels.get(stage, stage)


def generate_badge(
    pet: PetEngine,
    config: Config,
    today_stats: dict | None = None,
) -> str:
    """Generate an SVG badge string.

    Args:
        pet: Current pet state.
        config: User configuration.
        today_stats: Optional dict with session_count, total_calls, detected_type.

    Returns:
        SVG XML string.
    """
    stats = today_stats or {}
    sessions = stats.get("session_count", 0)
    calls = stats.get("total_calls", 0)
    work_type = stats.get("detected_type", "")

    mood_emoji = _mood_emoji(pet.mood)
    stage_label = _stage_label(pet.stage)

    # Build CSS custom properties for theming
    css_vars = "\n".join(
        f"      --tomo-{key}: {value['dark']};"
        f" --tomo-{key}-light: {value['light']};"
        for key, value in COLORS.items()
    )

    # Content layout (right side)
    content_x = 140
    content_y = 36
    line_height = 22

    # Pet name & level
    header = (
        f'<text x="{content_x}" y="{content_y}" '
        f'class="tomo-name">{config.pet_name}</text>\n'
        f'<text x="{content_x}" y="{content_y + line_height}" '
        f'class="tomo-level">lv.{pet.level}  {stage_label}  {mood_emoji}</text>\n'
    )

    # Stats bars
    bar_y = content_y + line_height * 2 + 4
    bars = (
        f'<text x="{content_x}" y="{bar_y}" class="tomo-label">能量</text>\n'
        + _bar_svg(
            pet.energy, x=content_x + 36, y=bar_y - 10,
            color_key="energy",
        )
        + f'<text x="{content_x}" y="{bar_y + 16}" class="tomo-label">饱食</text>\n'
        + _bar_svg(
            pet.satiation, x=content_x + 36, y=bar_y + 6,
            color_key="satiation",
        )
    )

    # Today stats
    stats_y = bar_y + 44
    stats_lines = []
    if sessions:
        stats_lines.append(f"Sessions: {sessions}")
    if calls:
        stats_lines.append(f"Calls: {calls}")
    if work_type:
        stats_lines.append(f"Type: {work_type}")

    if stats_lines:
        stats_text = "  |  ".join(stats_lines)
        stats_svg = (
            f'<text x="{content_x}" y="{stats_y}" '
            f'class="tomo-stats">{stats_text}</text>\n'
        )
    else:
        stats_svg = (
            f'<text x="{content_x}" y="{stats_y}" '
            f'class="tomo-stats">今日暂无数据</text>\n'
        )

    # Affinity line
    affinity_y = stats_y + line_height + 4
    affinity_svg = (
        f'<text x="{content_x}" y="{affinity_y}" '
        f'class="tomo-affinity">'
        f'亲密度: {pet.affinity}'
        f'</text>\n'
    )

    # ASCII avatar (left side) - simplified single-line representation
    avatar_x = PADDING + 10
    avatar_y = 60
    avatar_size = 48

    # Use the pet avatar emoji as a large icon
    avatar_svg = (
        f'<text x="{avatar_x}" y="{avatar_y}" '
        f'class="tomo-avatar" font-size="{avatar_size}">'
        f'{config.pet_avatar}'
        f'</text>\n'
    )

    # Stage icon below avatar
    stage_icon_y = avatar_y + 28
    stage_svg = (
        f'<text x="{avatar_x}" y="{stage_icon_y}" '
        f'class="tomo-stage">{stage_label}</text>\n'
    )

    # Build CSS classes without long lines
    _font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    _emoji_font = "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif"
    css_rules = [
        ".bg { fill: var(--tomo-bg); }",
        ".border { fill: none; stroke: var(--tomo-border); stroke-width: 1; rx: 8; }",
        f".tomo-name {{ font: bold 16px {_font}; fill: var(--tomo-text-primary); }}",
        f".tomo-level {{ font: 13px {_font}; fill: var(--tomo-text-secondary); }}",
        f".tomo-label {{ font: 11px {_font}; fill: var(--tomo-text-secondary); }}",
        f".tomo-stats {{ font: 12px {_font}; fill: var(--tomo-accent); }}",
        f".tomo-affinity {{ font: 11px {_font}; fill: var(--tomo-mood); }}",
        f".tomo-avatar {{ font: 48px {_emoji_font}; fill: var(--tomo-text-primary); }}",
        f".tomo-stage {{ font: 11px {_font}; fill: var(--tomo-text-secondary); }}",
    ]
    css_classes = "\n      ".join(css_rules)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BADGE_WIDTH}" '
        f'height="{BADGE_HEIGHT}">\n'
        f"  <defs>\n"
        f"    <style>\n"
        f"      :root {{\n"
        f"        {css_vars}\n"
        f"        --tomo-track: #30363d;\n"
        f"        --tomo-track-light: #eaeef2;\n"
        f"      }}\n"
        f"      @media (prefers-color-scheme: light) {{\n"
        f"        :root {{\n"
        f"          --tomo-bg: var(--tomo-bg-light);\n"
        f"          --tomo-border: var(--tomo-border-light);\n"
        f"          --tomo-text-primary: var(--tomo-text-primary-light);\n"
        f"          --tomo-text-secondary: var(--tomo-text-secondary-light);\n"
        f"          --tomo-accent: var(--tomo-accent-light);\n"
        f"          --tomo-energy: var(--tomo-energy-light);\n"
        f"          --tomo-satiation: var(--tomo-satiation-light);\n"
        f"          --tomo-mood: var(--tomo-mood-light);\n"
        f"          --tomo-track: var(--tomo-track-light);\n"
        f"        }}\n"
        f"      }}\n"
        f"      @media (prefers-color-scheme: dark) {{\n"
        f"        :root {{\n"
        f"          --tomo-bg: var(--tomo-bg-dark);\n"
        f"          --tomo-border: var(--tomo-border-dark);\n"
        f"          --tomo-text-primary: var(--tomo-text-primary-dark);\n"
        f"          --tomo-text-secondary: var(--tomo-text-secondary-dark);\n"
        f"          --tomo-accent: var(--tomo-accent-dark);\n"
        f"          --tomo-energy: var(--tomo-energy-dark);\n"
        f"          --tomo-satiation: var(--tomo-satiation-dark);\n"
        f"          --tomo-mood: var(--tomo-mood-dark);\n"
        f"          --tomo-track: var(--tomo-track-dark);\n"
        f"        }}\n"
        f"      }}\n"
        f"      {css_classes}\n"
        f"    </style>\n"
        f"  </defs>\n"
        f'  <rect class="bg" width="100%" height="100%" rx="8"/>\n'
        f'  <rect class="border" x="0.5" y="0.5" '
        f'width="{BADGE_WIDTH - 1}" height="{BADGE_HEIGHT - 1}"/>\n'
        f"  {avatar_svg}"
        f"  {stage_svg}"
        f"  {header}"
        f"  {bars}"
        f"  {stats_svg}"
        f"  {affinity_svg}"
        f"</svg>"
    )

    return svg


def generate_workflow_yaml() -> str:
    """Return a GitHub Actions workflow YAML for auto-updating the badge."""
    return """name: Update Tomo Badge

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  update-badge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Tomo
        run: pip install tomo
      - name: Generate badge
        run: tomo badge --output tomo-badge.svg
      - name: Commit badge
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add tomo-badge.svg
          git diff --cached --quiet || git commit -m "Update Tomo badge [automated]"
          git push
"""
