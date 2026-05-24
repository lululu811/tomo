# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Multi-species system: support fox, cat, and dragon with unique ASCII art and dialogue.
- `tomo species` CLI command with `--list` and `--switch` options.
- Species template system via YAML files (`templates/*.yaml`).
- Programmer-encourager personality styles: encourager, roaster, anime, default.
- Dynamic system prompt builder that incorporates coding stats, mood, and achievements.
- Easter egg detection: commit message keywords, code patterns (TODO/FIXME/HACK), late-night commits, mass deletions.
- Daemon integration for easter eggs with 30-minute cooldown and desktop notifications.
- Memory and affinity system: key-value memory store with categories, auto-extraction from chat messages, and intimacy score with 6 relationship levels.
- `tomo remember`, `tomo memories`, `tomo forget` CLI commands.
- Achievement share card: `tomo share` with Rich terminal rendering, ASCII plain-text output, and HTML export.
- GitHub Profile Badge: `tomo badge` generates SVG with dark/light theme adaptation, includes pet status and coding stats.
- `tomo badge --github` outputs GitHub Actions workflow YAML for automated badge updates.
- 200+ test cases covering species, easter eggs, memory, affinity, share cards, badge generator, prompt builder, and CLI.

## [0.1.0] - 2025-05-24

### Added

- Initial release of Tomo.
- Pet engine with experience, level, energy, satiation, mood, and 5 evolution stages (egg to adult).
- Claude Code session stats detector (`detector.py`).
- Background daemon with automatic syncing, achievement detection, and desktop notifications.
- Multi-provider LLM client supporting Ollama, Anthropic, OpenAI, SiliconFlow, DeepSeek, and Minimax.
- SQLite database for persistent state, growth logs, chat history, and daily stats.
- Rich CLI with shell integration support (zsh, bash, fish).
- Achievement system with 11 unlockable achievements.
- Self-update functionality via git pull or pip upgrade.
- Cross-platform desktop notifications via plyer with fallback commands.
- GitHub token authentication for update checks to avoid API rate limits.
