import * as vscode from 'vscode';
import { getPetState, PetState } from './cli';

const MOOD_EMOJIS: Record<string, string> = {
    energetic: '⚡',
    happy: '😊',
    neutral: '😐',
    tired: '😴',
    exhausted: '💀',
};

export class TomoStatusBar implements vscode.Disposable {
    private item: vscode.StatusBarItem;
    private interval: NodeJS.Timeout | undefined;
    private clickHandler: (() => void) | undefined;

    constructor() {
        this.item = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.item.command = 'tomo.openPanel';
    }

    show() {
        this.item.show();
        this.refresh();

        // Auto-refresh
        const config = vscode.workspace.getConfiguration('tomo');
        const intervalSec = config.get<number>('refreshInterval', 30);
        this.interval = setInterval(() => this.refresh(), intervalSec * 1000);
    }

    async refresh() {
        const state = await getPetState();
        if (state) {
            this.item.text = this.formatStatus(state);
            this.item.tooltip = `Tomo - ${state.stage} | Energy: ${state.energy}/100 | Satiation: ${state.satiation}/100`;
        } else {
            this.item.text = '$(heart) Tomo';
            this.item.tooltip = 'Tomo status unavailable. Run `tomo init` in terminal.';
        }
    }

    private formatStatus(state: PetState): string {
        const mood = MOOD_EMOJIS[state.mood] || '😐';
        return `$(heart) ${state.name} lv.${state.level} ${mood}`;
    }

    onClick(handler: () => void) {
        this.clickHandler = handler;
    }

    dispose() {
        if (this.interval) {
            clearInterval(this.interval);
        }
        this.item.dispose();
    }
}
