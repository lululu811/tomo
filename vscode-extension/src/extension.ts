import * as vscode from 'vscode';
import { TomoStatusBar } from './statusBar';
import { TomoPanel } from './panel';
import { execTomo } from './cli';

let statusBar: TomoStatusBar | undefined;
let panel: TomoPanel | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Tomo extension activated');

    // Initialize status bar
    statusBar = new TomoStatusBar();
    statusBar.show();

    // Register commands
    const disposables = [
        vscode.commands.registerCommand('tomo.chat', async () => {
            const msg = await vscode.window.showInputBox({
                prompt: 'Say something to Tomo...',
                placeHolder: 'How are you doing?',
            });
            if (msg) {
                const reply = await execTomo(`chat "${msg}"`);
                vscode.window.showInformationMessage(reply || 'Tomo is thinking...');
            }
        }),

        vscode.commands.registerCommand('tomo.status', async () => {
            const status = await execTomo('status');
            vscode.window.showInformationMessage(status || 'Tomo status unavailable');
        }),

        vscode.commands.registerCommand('tomo.feed', async () => {
            const result = await execTomo('feed');
            vscode.window.showInformationMessage(result || 'Fed Tomo!');
            statusBar?.refresh();
        }),

        vscode.commands.registerCommand('tomo.rest', async () => {
            const result = await execTomo('rest');
            vscode.window.showInformationMessage(result || 'Tomo is resting...');
            statusBar?.refresh();
        }),

        vscode.commands.registerCommand('tomo.play', async () => {
            const result = await execTomo('play');
            vscode.window.showInformationMessage(result || 'Played with Tomo!');
            statusBar?.refresh();
        }),

        vscode.commands.registerCommand('tomo.openPanel', () => {
            if (!panel) {
                panel = new TomoPanel(context.extensionUri);
            }
            panel.reveal();
        }),

        // Status bar click opens panel
        statusBar.onClick(() => {
            if (!panel) {
                panel = new TomoPanel(context.extensionUri);
            }
            panel.reveal();
        }),
    ];

    context.subscriptions.push(...disposables, statusBar);

    // Set context for view visibility
    vscode.commands.executeCommand('setContext', 'tomo.enabled', true);
}

export function deactivate() {
    statusBar?.dispose();
    panel?.dispose();
}
