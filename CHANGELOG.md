# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub token authentication for update checks to avoid API rate limits.

## [0.1.0] - 2025-05-24

### Added

- Initial release of Tomo.
- Pet engine with experience, level, energy, satiation, and mood system.
- Claude Code session stats detector (`detector.py`).
- Background daemon with automatic syncing, achievement detection, and desktop notifications.
- Multi-provider LLM client supporting Ollama, Anthropic, OpenAI, SiliconFlow, DeepSeek, and Minimax.
- SQLite database for persistent state, growth logs, chat history, and daily stats.
- Rich CLI with shell integration support (zsh, bash, fish).
- Achievement system with 11 unlockable achievements.
- Self-update functionality via git pull or pip upgrade.
- Cross-platform desktop notifications via plyer with fallback commands.
