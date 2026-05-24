import * as vscode from 'vscode';
import { getPetState, execTomo, PetState } from './cli';

export class TomoPanel implements vscode.Disposable {
    private panel: vscode.WebviewPanel | undefined;
    private extensionUri: vscode.Uri;
    private interval: NodeJS.Timeout | undefined;

    constructor(extensionUri: vscode.Uri) {
        this.extensionUri = extensionUri;
    }

    reveal() {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'tomoPanel',
            'Tomo',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        this.panel.onDidDispose(() => {
            this.panel = undefined;
            if (this.interval) {
                clearInterval(this.interval);
            }
        });

        this.refresh();
        this.interval = setInterval(() => this.refresh(), 30000);
    }

    async refresh() {
        if (!this.panel) return;

        const state = await getPetState();
        this.panel.webview.html = this.getHtml(state);

        // Handle messages from webview
        this.panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'feed':
                    await execTomo('feed');
                    break;
                case 'rest':
                    await execTomo('rest');
                    break;
                case 'play':
                    await execTomo('play');
                    break;
                case 'chat':
                    if (message.text) {
                        await execTomo(`chat "${message.text}"`);
                    }
                    break;
                case 'refresh':
                    await this.refresh();
                    break;
            }
            // Refresh after action
            setTimeout(() => this.refresh(), 1000);
        });
    }

    private getHtml(state: PetState | null): string {
        const isDark = vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.Dark;
        const bg = isDark ? '#0d1117' : '#ffffff';
        const text = isDark ? '#c9d1d9' : '#1f2328';
        const textSecondary = isDark ? '#8b949e' : '#656d76';
        const border = isDark ? '#30363d' : '#d0d7de';
        const accent = isDark ? '#58a6ff' : '#0969da';
        const energyColor = isDark ? '#3fb950' : '#1a7f37';
        const satColor = isDark ? '#d29922' : '#bc4c00';

        if (!state) {
            return `<!DOCTYPE html>
<html><body style="background:${bg};color:${text};font-family:sans-serif;text-align:center;padding:40px;">
<h2>Tomo not initialized</h2>
<p>Run <code>tomo init</code> in your terminal first.</p>
</body></html>`;
        }

        const moodEmojis: Record<string, string> = {
            energetic: '⚡', happy: '😊', neutral: '😐', tired: '😴', exhausted: '💀',
        };
        const moodEmoji = moodEmojis[state.mood] || '😐';
        const energyBar = this.renderBar(state.energy, 100, energyColor);
        const satBar = this.renderBar(state.satiation, 100, satColor);

        return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {
  background: ${bg};
  color: ${text};
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  padding: 20px;
  max-width: 400px;
  margin: 0 auto;
}
.avatar {
  font-size: 64px;
  text-align: center;
  margin: 20px 0;
}
.name {
  font-size: 24px;
  font-weight: bold;
  text-align: center;
  margin: 10px 0;
}
.info {
  text-align: center;
  color: ${textSecondary};
  margin-bottom: 20px;
}
.bar-container {
  margin: 12px 0;
}
.bar-label {
  font-size: 12px;
  color: ${textSecondary};
  margin-bottom: 4px;
}
.bar-track {
  background: ${border};
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.affinity {
  text-align: center;
  margin: 16px 0;
  font-size: 14px;
  color: ${textSecondary};
}
.actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin: 20px 0;
}
button {
  background: ${accent};
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
button:hover {
  opacity: 0.9;
}
.chat-box {
  margin-top: 20px;
  display: flex;
  gap: 8px;
}
input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid ${border};
  border-radius: 6px;
  background: ${bg};
  color: ${text};
  font-size: 14px;
}
</style>
</head>
<body>
<div class="avatar">${state.avatar}</div>
<div class="name">${state.name} lv.${state.level} ${moodEmoji}</div>
<div class="info">${state.stage} | Energy: ${state.energy}/100 | Sat: ${state.satiation}/100</div>

<div class="bar-container">
  <div class="bar-label">Energy</div>
  <div class="bar-track"><div class="bar-fill" style="width:${state.energy}%;background:${energyColor}"></div></div>
</div>
<div class="bar-container">
  <div class="bar-label">Satiation</div>
  <div class="bar-track"><div class="bar-fill" style="width:${state.satiation}%;background:${satColor}"></div></div>
</div>

<div class="affinity">Affinity: ${state.affinity}</div>

<div class="actions">
  <button onclick="send('feed')">Feed</button>
  <button onclick="send('rest')">Rest</button>
  <button onclick="send('play')">Play</button>
  <button onclick="send('refresh')">Refresh</button>
</div>

<div class="chat-box">
  <input type="text" id="chatInput" placeholder="Say something to Tomo..." onkeypress="if(event.key==='Enter')sendChat()">
  <button onclick="sendChat()">Chat</button>
</div>

<script>
const vscode = acquireVsCodeApi();
function send(cmd) { vscode.postMessage({ command: cmd }); }
function sendChat() {
  const input = document.getElementById('chatInput');
  if (input.value) {
    vscode.postMessage({ command: 'chat', text: input.value });
    input.value = '';
  }
}
</script>
</body>
</html>`;
    }

    private renderBar(value: number, max: number, color: string): string {
        const pct = Math.min(100, Math.max(0, (value / max) * 100));
        return `<div style="background:#30363d;border-radius:4px;height:8px;"><div style="width:${pct}%;background:${color};height:100%;border-radius:4px;"></div></div>`;
    }

    dispose() {
        if (this.interval) {
            clearInterval(this.interval);
        }
        this.panel?.dispose();
    }
}
