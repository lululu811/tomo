# Tomo VS Code Extension

Your virtual pet companion right in VS Code.

## Features

- **Status Bar**: Shows pet emoji, level, and mood. Auto-refreshes every 30 seconds.
- **Side Panel**: Click the status bar to open a full pet panel with:
  - Pet avatar and stats (energy, satiation, affinity)
  - Quick action buttons: Feed, Rest, Play
  - Chat input to talk to Tomo
- **Commands**: Access via Command Palette (`Ctrl+Shift+P`):
  - `Tomo: Chat` - Talk to your pet
  - `Tomo: Status` - Show current status
  - `Tomo: Feed` / `Tomo: Rest` / `Tomo: Play`
  - `Tomo: Open Panel` - Open the pet panel

## Requirements

- [Tomo CLI](https://github.com/lululu811/tomo) must be installed and initialized (`tomo init`)
- VS Code 1.80+

## Installation

### From Source

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to open Extension Host for testing
```

### Build VSIX

```bash
npm install -g vsce
vsce package
# Install the generated .vsix file in VS Code
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `tomo.refreshInterval` | 30 | Status bar refresh interval in seconds |
| `tomo.cliPath` | `tomo` | Path to the tomo CLI executable |

## License

MIT
