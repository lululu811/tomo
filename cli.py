"""CLI entry point for Tomo."""

import logging
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tomo import __version__
from tomo.achievements import AchievementChecker
from tomo.config import Config, ensure_default_config, load_config
from tomo.db import Database
from tomo.detector import StatsDetector
from tomo.logging_config import setup_logging
from tomo.pet_engine import PetEngine
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

def _load_stage_art() -> dict[str, str]:
    """Load stage ASCII art from template YAML."""
    template_path = Path(__file__).parent / "templates" / "default_fox.yaml"
    if not template_path.exists():
        return {}
    try:
        data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        stages = data.get("stages", {})
        return {k: v.rstrip("\n") for k, v in stages.items() if isinstance(v, str)}
    except Exception:
        return {}


# Cache stage art on first use
_STAGE_ART: dict[str, str] | None = None


def _get_stage_art() -> dict[str, str]:
    global _STAGE_ART
    if _STAGE_ART is None:
        _STAGE_ART = _load_stage_art()
    return _STAGE_ART


def _get_pet_avatar(stage: str) -> str:
    """Return ASCII avatar based on evolution stage."""
    art = _get_stage_art()
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

    avatar = _get_pet_avatar(pet.stage)
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

    content = (
        f"[cyan]{avatar}[/cyan]\n"
        f"\n"
        f"[bold]{config.pet_name}[/bold] lv.{pet.level} {mood_emoji} | Stage: {stage_label}\n"
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

    # Build system prompt from personality config
    personality = config.personality
    speech = personality.get("speech", {})
    forbidden_list = speech.get("forbidden", [])
    forbidden = ", ".join(forbidden_list) if forbidden_list else "无"

    system_prompt = (
        f"你是 {config.pet_name}，"
        f"{personality.get('description', '一只好奇的小狐狸')}。\n"
        f"当前状态：{pet.mood}，等级 lv.{pet.level}，"
        f"能量 {pet.energy}/100，饱食度 {pet.satiation}/100。\n"
        f"说话风格：{speech.get('style', 'casual, short, uses emoji')}，"
        f"语气：{speech.get('tone', 'warm, healing, slightly playful')}。\n"
        f"禁止：{forbidden}\n"
        f"你能记住之前的对话内容，请根据上下文自然回复。\n"
        f"请用简短温暖的中文回复用户。"
    )

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

    # Display response
    console.print(f"{config.pet_avatar} [bold]{config.pet_name}[/bold]: {response}")
