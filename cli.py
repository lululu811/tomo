"""CLI entry point for Tomo."""

import logging
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tomo import __version__
from tomo.achievements import ACHIEVEMENTS, AchievementChecker
from tomo.badge_generator import generate_badge, generate_workflow_yaml
from tomo.config import Config, ensure_default_config, load_config
from tomo.db import Database
from tomo.detector import StatsDetector
from tomo.logging_config import setup_logging
from tomo.memory_manager import MemoryManager
from tomo.pet_engine import PetEngine
from tomo.share_card import build_ascii_card, build_html_card, build_share_card
from tomo.species_manager import get_species, list_available_species
from tomo.updater import backup_database, check_update, perform_update

logger = logging.getLogger(__name__)

console = Console()


def _tomo_dir() -> Path:
    return Path.home() / ".tomo"


def _db_path() -> Path:
    return _tomo_dir() / "tomo.db"


def _config_path() -> Path:
    return _tomo_dir() / "config.yaml"


MOOD_EMOJIS = {
    "energetic": "⚡",
    "happy": "😊",
    "neutral": "😐",
    "tired": "😴",
    "exhausted": "💀",
}

MOOD_MESSAGES = {
    "energetic": [
        "Ready to tackle anything!",
        "Full of energy today!",
        "Let's build something amazing!",
    ],
    "happy": [
        "Feeling good!",
        "Nice to see you!",
        "Let's have a productive day!",
    ],
    "neutral": [
        "Just chilling here.",
        "Waiting for you to start.",
        "Another day, another session.",
    ],
    "tired": [
        "Could use a break...",
        "Getting a bit sleepy.",
        "Maybe some rest soon?",
    ],
    "exhausted": [
        "Need rest urgently...",
        "Running on empty...",
        "Please let me rest...",
    ],
}

def _load_stage_art(species: str = "fox") -> dict[str, str]:
    """Load stage ASCII art from species template YAML."""
    from tomo.species_manager import get_species

    template = get_species(species)
    stages = template.stages
    return {k: v.rstrip("\n") for k, v in stages.items() if isinstance(v, str)}


# Cache stage art per species
_STAGE_ART_CACHE: dict[str, dict[str, str]] = {}


def _get_stage_art(species: str = "fox") -> dict[str, str]:
    if species not in _STAGE_ART_CACHE:
        _STAGE_ART_CACHE[species] = _load_stage_art(species)
    return _STAGE_ART_CACHE[species]


def _get_pet_avatar(stage: str, species: str = "fox") -> str:
    """Return ASCII avatar based on evolution stage and species."""
    art = _get_stage_art(species)
    if stage in art:
        return art[stage]
    # Fallback to old level-based avatars
    if stage == "adult":
        lines = [
            "    \\__/    ",
            "   ( o  o )   ",
            "   (  皿  )   ",
            "   /|    |\\   ",
            "    |    |    ",
        ]
    elif stage == "teen":
        lines = [
            "   /\\__/\\   ",
            "  ( o  o )  ",
            "  (   皿   )  ",
            "   /    \\   ",
        ]
    else:
        lines = [
            "  /\\_/\\  ",
            " ( o.o ) ",
            "  > ^ <  ",
        ]
    return "\n".join(lines)


PLAY_MESSAGES = [
    "You tossed a virtual ball!",
    "You gave some head pats!",
    "You played a quick game!",
    "You told a joke!",
    "You danced together!",
]

FEED_MESSAGES = [
    "Yum! That was tasty!",
    "Delicious! More please!",
    "Munch munch... thanks!",
    "That hit the spot!",
    "So satisfying!",
]

REST_MESSAGES = [
    "Zzz... feeling refreshed!",
    "A nice power nap!",
    "Energy restored!",
    "Ready to go again!",
    "That was relaxing!",
]

SHELL_SNIPPETS = {
    "zsh": """
# Add to ~/.zshrc
export PS1='$(tomo prompt) '$PS1
""",
    "bash": """
# Add to ~/.bashrc
export PS1='$(tomo prompt) '$PS1
""",
    "fish": r"""
# Add to ~/.config/fish/config.fish
function fish_prompt
    echo (tomo prompt) (prompt_pwd) \>
end
""",
}




def _bar(value: int, max_val: int = 100, color: str = "green") -> str:
    """Return a simple text bar."""
    filled = int(value / max_val * 20)
    empty = 20 - filled
    bar = "█" * filled + "░" * empty
    return f"[{color}]{bar}[/{color}] {value}/{max_val}"


def _energy_color(energy: int) -> str:
    if energy >= 80:
        return "green"
    elif energy >= 50:
        return "yellow"
    elif energy >= 20:
        return "orange3"
    return "red"


def _require_init() -> tuple[Database, Config]:
    """Check Tomo is initialized and return common objects."""
    db_path = _db_path()
    if not db_path.exists():
        console.print("[red]Tomo not initialized. Run `tomo init` first.[/red]")
        raise click.ClickException("Tomo not initialized")

    db = Database(db_path)
    config = load_config(_config_path())
    return db, config


@click.group()
@click.version_option(version=__version__, prog_name="tomo")
def main() -> None:
    """Tomo — your local AI companion."""
    setup_logging()


@main.command()
def init() -> None:
    """Initialize Tomo in ~/.tomo/."""
    tomo_dir = _tomo_dir()
    tomo_dir.mkdir(parents=True, exist_ok=True)
    config_path = ensure_default_config()
    Database(_db_path())
    config = load_config(config_path)

    welcome_text = (
        f"[bold]Welcome![/bold] Your companion [bold]{config.pet_name}[/bold] "
        f"has been initialized.\n"
        f"Config: {config_path}\n"
        f"Database: {_db_path()}"
    )
    console.print(Panel(welcome_text, title="🦊 Tomo", border_style="green"))


@main.command()
def status() -> None:
    """Show Tomo's current status."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    work_type, confidence = db.detect_type_from_cwd(os.getcwd())
    detector = StatsDetector()
    snapshot = detector.read_latest()

    # Check achievements
    checker = AchievementChecker(db)
    new_achievements = checker.check(snapshot, pet.level)
    if new_achievements:
        checker.log_unlocked(new_achievements)

    unlocked = checker.get_unlocked_achievements(limit=10)

    mood_emoji = MOOD_EMOJIS.get(pet.mood, "😐")
    energy_color = _energy_color(pet.energy)

    work_info = "No work detected"
    if work_type:
        work_info = f"{work_type} ({confidence * 100:.0f}%)"

    avatar = _get_pet_avatar(pet.stage, config.species)
    stage_label = pet.stage.capitalize()

    # Achievement display
    achievement_text = ""
    if unlocked:
        achievement_text = "\n[bold]Achievements:[/bold] " + " ".join(
            f"{a.icon} {a.name}" for a in unlocked[:5]
        )
    if new_achievements:
        achievement_text += "\n[bold green]New unlocks:[/bold green] " + " ".join(
            f"{a.icon} {a.name}" for a in new_achievements
        )

    # Affinity display
    mem_mgr = MemoryManager(db)
    affinity_display = mem_mgr.get_affinity_display()

    content = (
        f"[cyan]{avatar}[/cyan]\n"
        f"\n"
        f"[bold]{config.pet_name}[/bold] lv.{pet.level} {mood_emoji} | Stage: {stage_label}\n"
        f"{affinity_display}\n"
        f"\n"
        f"Energy:    {_bar(pet.energy, color=energy_color)}\n"
        f"Satiation: {_bar(pet.satiation, color='cyan')}\n"
        f"Progress:  {_bar(int(pet.level_progress * 100), max_val=100, color='magenta')} "
        f"(to lv.{pet.level + 1})\n"
        f"\n"
        f"Today's work: {work_info}\n"
        f"Sessions: {snapshot.session_count} | Total calls: {snapshot.total_calls}\n"
        f"\n"
        f"[italic]{random.choice(MOOD_MESSAGES.get(pet.mood, MOOD_MESSAGES['neutral']))}[/italic]"
        f"{achievement_text}"
    )

    console.print(
        Panel(content, title=f"{config.pet_avatar} {config.pet_name}", border_style="blue")
    )


@main.command()
def feed() -> None:
    """Feed Tomo to increase satiation."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    old_satiation = pet.satiation
    pet.feed(15)
    gained = pet.satiation - old_satiation

    db.set_pet_state("satiation", str(pet.satiation))
    db.log_growth_event(
        "interaction",
        f"Fed {config.pet_name}. Satiation +{gained}.",
    )

    # Affinity
    mem_mgr = MemoryManager(db)
    level = mem_mgr.add_affinity("feed")
    _maybe_affinity_message(level, config)

    msg = random.choice(FEED_MESSAGES)
    console.print(
        f"[green]{config.pet_avatar} {msg}[/green] (Satiation: {old_satiation} -> {pet.satiation})"
    )


@main.command()
def rest() -> None:
    """Let Tomo rest to recover energy."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    old_energy = pet.energy
    pet.rest(25)
    gained = pet.energy - old_energy

    db.set_pet_state("energy", str(pet.energy))
    db.log_growth_event(
        "interaction",
        f"{config.pet_name} rested. Energy +{gained}.",
    )

    # Affinity
    mem_mgr = MemoryManager(db)
    level = mem_mgr.add_affinity("rest")
    _maybe_affinity_message(level, config)

    msg = random.choice(REST_MESSAGES)
    console.print(f"[blue]{config.pet_avatar} {msg}[/blue] (Energy: {old_energy} -> {pet.energy})")


@main.command()
def play() -> None:
    """Play with Tomo (costs energy, but boosts mood)."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    if pet.energy < 10:
        console.print(
            f"[red]{config.pet_avatar} {config.pet_name} is too tired to play. "
            f"Try `tomo rest` first![/red]"
        )
        return

    old_energy = pet.energy
    pet.consume_energy(10)
    # Playing also makes them a bit hungry
    pet.satiation = max(0, pet.satiation - 5)

    db.set_pet_state("energy", str(pet.energy))
    db.set_pet_state("satiation", str(pet.satiation))
    db.log_growth_event(
        "interaction",
        f"Played with {config.pet_name}. Energy -10, Satiation -5.",
    )

    # Affinity
    mem_mgr = MemoryManager(db)
    level = mem_mgr.add_affinity("play")
    _maybe_affinity_message(level, config)

    msg = random.choice(PLAY_MESSAGES)
    console.print(
        f"[magenta]{config.pet_avatar} {msg}[/magenta] (Energy: {old_energy} -> {pet.energy})"
    )


@main.command()
@click.option("--days", default=7, help="Number of days to report.")
def report(days: int) -> None:
    """Show work statistics report."""
    db, config = _require_init()
    detector = StatsDetector()
    snapshot = detector.read_latest()

    # Get recent logs for stats
    logs = db.get_growth_logs(limit=100)

    table = Table(title=f"📊 {config.pet_name}'s Work Report (last {days} days)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Sessions", str(snapshot.session_count))
    table.add_row("Total Tool Calls", str(snapshot.total_calls))
    table.add_row("Skill Calls", str(snapshot.skill_calls))

    # Tool breakdown
    if snapshot.tool_breakdown:
        top_tools = sorted(snapshot.tool_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
        tools_str = ", ".join(f"{tool} ({count})" for tool, count in top_tools)
        table.add_row("Top Tools", tools_str)
    else:
        table.add_row("Top Tools", "No data yet")

    # Work type
    work_type, confidence = db.detect_type_from_cwd(os.getcwd())
    if work_type:
        table.add_row("Current Work Type", f"{work_type} ({confidence * 100:.0f}%)")
    else:
        table.add_row("Current Work Type", "Unknown")

    # Growth events count
    event_count = len([log for log in logs if log.get("event_type") == "interaction"])
    table.add_row("Interactions", str(event_count))

    console.print(table)


@main.command()
@click.option("--limit", default=20, help="Number of log entries to show.")
def logs(limit: int) -> None:
    """Show Tomo's growth and interaction logs."""
    db, _ = _require_init()
    log_entries = db.get_growth_logs(limit=limit)

    if not log_entries:
        console.print("[italic]No logs yet. Start working and interacting with Tomo![/italic]")
        return

    table = Table(title="📜 Growth Log")
    table.add_column("Time", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Event", style="green")

    for entry in log_entries:
        ts = entry.get("timestamp", "Unknown")[:19]  # Trim to seconds
        event_type = entry.get("event_type", "unknown")
        desc = entry.get("description", "No description")
        table.add_row(ts, event_type, desc)

    console.print(table)


@main.command()
def prompt() -> None:
    """Output compact prompt string for shell integration."""
    db_path = _db_path()
    if not db_path.exists():
        return

    db = Database(db_path)
    config = load_config(_config_path())
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)
    mood_emoji = MOOD_EMOJIS.get(pet.mood, "😐")
    click.echo(f"[{config.pet_avatar} {config.pet_name} lv.{pet.level} {mood_emoji}]")


@main.command()
@click.option("--shell", type=click.Choice(["zsh", "bash", "fish"]), default="zsh")
def install(shell: str) -> None:
    """Show shell integration snippet."""
    snippet = SHELL_SNIPPETS.get(shell, SHELL_SNIPPETS["zsh"])
    console.print(Panel(snippet.strip(), title=f"{shell} Integration", border_style="green"))


@main.command()
@click.option("--check", is_flag=True, help="Only check for updates, don't install")
def update(check: bool) -> None:
    """Check for and install updates."""
    info = check_update(__version__)

    if check:
        console.print(
            f"Current version: [cyan]{info.current_version}[/cyan] "
            f"([dim]{info.current_commit}[/dim])"
        )
        console.print(f"Latest version:  [cyan]{info.latest_commit}[/cyan]")
        if info.needs_update:
            console.print(
                "[yellow]A new version is available! Run `tomo update` to install.[/yellow]"
            )
        else:
            console.print("[green]You are on the latest version.[/green]")
        return

    if not info.needs_update:
        console.print("[green]You are already on the latest version.[/green]")
        return

    console.print(f"Current: [dim]{info.current_commit}[/dim]")
    console.print(f"Latest:  [cyan]{info.latest_commit}[/cyan]")
    console.print()

    # Backup database
    tomo_dir = _tomo_dir()
    backup_path = backup_database(tomo_dir)
    if backup_path:
        console.print(f"[green]Database backed up to {backup_path.name}[/green]")
    else:
        console.print("[yellow]No database found to backup.[/yellow]")

    console.print()
    console.print("[bold]Updating tomo...[/bold]")

    success, message = perform_update()
    if success:
        console.print(f"[green]{message}[/green]")
        console.print("[bold]Update complete! Restart your terminal to use the new version.[/bold]")
    else:
        console.print(f"[red]{message}[/red]")
        raise click.ClickException("Update failed")


@main.group()
def daemon() -> None:
    """Manage Tomo background daemon."""
    pass


@daemon.command()
@click.option("--interval", default=300, help="Sync interval in seconds")
def start(interval: int) -> None:
    """Start the background daemon."""
    from tomo import daemon as daemon_module

    if daemon_module.is_running():
        console.print("[yellow]Daemon is already running.[/yellow]")
        return

    daemon_script = Path(__file__).parent / "daemon.py"
    # Daemon itself redirects stdout/stderr to ~/.tomo/daemon.log
    popen_kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(
        [sys.executable, str(daemon_script), "--interval", str(interval)],
        **popen_kwargs,  # type: ignore[call-overload]
    )

    # Wait for PID file to appear
    for _ in range(10):
        if daemon_module.is_running():
            pid = daemon_module.get_pid()
            console.print(f"[green]Daemon started (PID {pid}).[/green]")
            return
        time.sleep(0.2)

    console.print("[red]Failed to start daemon.[/red]")


@daemon.command()
def stop() -> None:
    """Stop the background daemon."""
    from tomo import daemon as daemon_module

    if not daemon_module.is_running():
        console.print("[yellow]Daemon is not running.[/yellow]")
        return

    if daemon_module.stop_daemon():
        console.print("[green]Daemon stopped.[/green]")
    else:
        console.print("[red]Failed to stop daemon.[/red]")


@daemon.command("status")
def daemon_status() -> None:
    """Check daemon status."""
    from tomo import daemon as daemon_module

    if daemon_module.is_running():
        pid = daemon_module.get_pid()
        console.print(f"[green]Daemon is running (PID {pid}).[/green]")
    else:
        console.print("[yellow]Daemon is not running.[/yellow]")


@main.command()
def growth() -> None:
    """Show pet growth and experience history."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    exp_history = db.get_exp_history(limit=14)

    # Build simple ASCII bar chart of recent exp gains
    chart = ""
    if exp_history:
        max_exp = max(e["exp_gained"] for e in exp_history)
        for entry in exp_history[-7:]:  # Last 7 entries
            bar_len = int(entry["exp_gained"] / max_exp * 10) if max_exp > 0 else 0
            bar = "█" * bar_len + "░" * (10 - bar_len)
            chart += f"  {entry['timestamp'][:10]} |{bar}| +{entry['exp_gained']}\n"

    from tomo.pet_engine import STAGE_THRESHOLDS

    stage_label = pet.stage.capitalize()
    next_stage = None
    for threshold, label in STAGE_THRESHOLDS:
        if pet.exp < threshold:
            next_stage = (label, threshold)
            break

    stage_info = f"进化阶段: {stage_label}"
    if next_stage:
        stage_info += f" (距离 {next_stage[0].capitalize()} 还需 {next_stage[1] - pet.exp} EXP)"
    else:
        stage_info += " (已达最终形态!)"

    content = (
        f"[bold]{config.pet_name}[/bold] 成长记录\n"
        f"\n"
        f"等级: lv.{pet.level}\n"
        f"经验: {pet.exp}\n"
        f"距离下一级: {pet.exp_to_next_level} EXP\n"
        f"进度: {_bar(int(pet.level_progress * 100), max_val=100, color='magenta')}\n"
        f"{stage_info}\n"
        f"\n"
        f"[bold]最近经验获取:[/bold]\n"
        f"{chart if chart else '暂无数据，快去工作吧！💪'}"
    )
    console.print(Panel(content, title=f"{config.pet_avatar} Growth", border_style="green"))


@main.command()
@click.argument("message")
def chat(message: str) -> None:
    """Chat with your pet."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    # Determine chat style from config
    style = config.personality.get("style", "encourager")

    # Build rich system prompt using the prompt builder
    from tomo.prompt_builder import build_system_prompt

    system_prompt = build_system_prompt(config, pet, db, style=style)

    # Load chat history from SQLite
    history = db.get_chat_history(limit=100)

    # Build standard messages array for multi-turn conversation
    messages = []
    for entry in history[-20:]:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": message})

    # Call LLM
    from tomo.llm import LLMClient

    client = LLMClient(config)
    response = client.generate(system_prompt=system_prompt, messages=messages)

    # Save to SQLite (transaction-safe)
    db.add_chat_entry("user", message)
    db.add_chat_entry("assistant", response)

    # Affinity + auto-extract memory
    mem_mgr = MemoryManager(db)
    level = mem_mgr.add_affinity("chat")
    _maybe_affinity_message(level, config)
    extracted = mem_mgr.store_extracted(message)
    for key in extracted:
        db.log_growth_event("memory", f"Extracted memory: {key}")

    # Display response
    console.print(f"{config.pet_avatar} [bold]{config.pet_name}[/bold]: {response}")


@main.command()
@click.option("--list", "list_flag", is_flag=True, help="List available species")
@click.option("--switch", "switch_to", type=str, help="Switch to a species")
def species(list_flag: bool, switch_to: str | None) -> None:
    """Show or change your pet species."""
    if list_flag:
        available = list_available_species()
        console.print("[bold]Available species:[/bold]")
        for s in available:
            template = get_species(s)
            marker = " *current*" if s == "fox" else ""
            console.print(f"  {s}: {template.description}{marker}")
        return

    db, config = _require_init()

    if switch_to:
        available = list_available_species()
        if switch_to not in available:
            console.print(f"[red]Unknown species: {switch_to}[/red]")
            console.print(f"Available: {', '.join(available)}")
            return

        # Update config
        config_path = _config_path()
        cfg_data = load_config(config_path)._data
        cfg_data.setdefault("pet", {})["species"] = switch_to
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg_data, f, allow_unicode=True, sort_keys=False)

        template = get_species(switch_to)
        console.print(
            f"[green]Species switched to {switch_to}![/green]\n"
            f"{template.description}"
        )
        return

    # Show current species
    current = config.species
    template = get_species(current)
    console.print(
        f"[bold]Current species:[/bold] {current}\n"
        f"{template.description}\n"
        f"Use [cyan]tomo species --list[/cyan] to see options or "
        f"[cyan]tomo species --switch cat[/cyan] to change."
    )


# ------------------------------------------------------------------ #
# Affinity helper
# ------------------------------------------------------------------ #

def _maybe_affinity_message(level: Any, config: Config) -> None:
    """Print affinity level-up message if title changed."""
    from tomo.memory_manager import AFFINITY_TITLES

    # Check if we just hit a threshold
    for threshold, title in AFFINITY_TITLES:
        if level.score == threshold and threshold > 0:
            console.print(f"[yellow]✨ 亲密度提升！你们现在是 '{title}' 了！[/yellow]")
            break


# ------------------------------------------------------------------ #
# Memory commands
# ------------------------------------------------------------------ #

@main.command("remember")
@click.argument("text")
@click.option("--as-key", default=None, help="Custom key for this memory.")
@click.option("--category", default="fact", help="Memory category.")
def remember_cmd(text: str, as_key: str | None, category: str) -> None:
    """Ask Tomo to remember something."""
    db, _config = _require_init()
    mem_mgr = MemoryManager(db)
    key = as_key if as_key else text[:30].lower().strip()
    mem_mgr.remember(key, text, category)
    mem_mgr.add_affinity("remember")
    console.print(f"[green]记住了：{text}[/green]")


@main.command("memories")
@click.option("--category", default=None, help="Filter by category.")
@click.option("--limit", default=20, help="Max memories to show.")
def memories_cmd(category: str | None, limit: int) -> None:
    """Show what Tomo remembers about you."""
    db, _config = _require_init()
    mem_mgr = MemoryManager(db)
    memories = mem_mgr.list_memories(category=category, limit=limit)
    if not memories:
        console.print("[dim]Tomo 还没记住什么事呢...多跟它聊聊天吧！[/dim]")
        return

    table = Table(title="Tomo 的记忆")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Memory", style="green")
    table.add_column("When", style="dim")

    for mem in memories:
        created = mem.get("created_at", "")[:10]
        table.add_row(mem.get("category", "fact"), mem.get("value", ""), created)

    console.print(table)


@main.command("forget")
@click.argument("key")
def forget_cmd(key: str) -> None:
    """Ask Tomo to forget something by key."""
    db, _config = _require_init()
    mem_mgr = MemoryManager(db)
    if mem_mgr.forget(key):
        console.print(f"[green]已经忘记 '{key}' 了。[/green]")
    else:
        console.print(f"[yellow]Tomo 本来就不记得 '{key}'。[/yellow]")


# ------------------------------------------------------------------ #
# Share card commands
# ------------------------------------------------------------------ #

@main.command("share")
@click.argument("achievement_key", required=False)
@click.option("--ascii", "is_ascii", is_flag=True, help="Output plain text version.")
@click.option("--export", "export_path", default=None, help="Export as HTML to path.")
def share_cmd(
    achievement_key: str | None,
    is_ascii: bool,
    export_path: str | None,
) -> None:
    """Share an achievement card."""
    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    checker = AchievementChecker(db)
    unlocked = checker.get_unlocked_achievements()

    if not unlocked:
        console.print("[dim]还没有解锁任何成就，快去工作吧！[/dim]")
        return

    # Pick achievement
    if achievement_key:
        ach = ACHIEVEMENTS.get(achievement_key)
        if not ach:
            console.print(f"[red]找不到成就 '{achievement_key}'。[/red]")
            return
        # Verify it's unlocked
        if achievement_key not in {a.key for a in unlocked}:
            console.print(f"[yellow]成就 '{achievement_key}' 还未解锁！[/yellow]")
            return
    else:
        ach = unlocked[0]  # Most recent

    # Get unlock time
    times = db.get_achievement_times()
    unlock_time = times.get(ach.key)

    if export_path:
        html = build_html_card(ach, pet, config, unlock_time)
        Path(export_path).write_text(html, encoding="utf-8")
        console.print(f"[green]已导出到 {export_path}[/green]")
        return

    if is_ascii:
        text = build_ascii_card(ach, pet, config, unlock_time)
        console.print(text)
        return

    card = build_share_card(ach, pet, config, unlock_time)
    console.print(card)


@main.command("badge")
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Output SVG path (default: ~/.tomo/badge.svg).",
)
@click.option(
    "--github",
    "show_workflow",
    is_flag=True,
    help="Print GitHub Actions workflow YAML to stdout.",
)
def badge_cmd(output_path: str | None, show_workflow: bool) -> None:
    """Generate a GitHub Profile badge SVG."""
    if show_workflow:
        console.print(generate_workflow_yaml())
        return

    db, config = _require_init()
    state = db.get_all_pet_state()
    pet = PetEngine.from_dict(state)

    # Get today's stats
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = db.get_daily_stats(today)

    svg = generate_badge(pet, config, today_stats)

    out = Path(output_path) if output_path else _tomo_dir() / "badge.svg"
    out.write_text(svg, encoding="utf-8")
    console.print(f"[green]Badge saved to {out}[/green]")
