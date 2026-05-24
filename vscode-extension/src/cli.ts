import * as cp from 'child_process';
import * as util from 'util';
import * as vscode from 'vscode';

const execAsync = util.promisify(cp.exec);

/**
 * Execute a tomo CLI command and return stdout.
 */
export async function execTomo(args: string): Promise<string | null> {
    const config = vscode.workspace.getConfiguration('tomo');
    const cliPath = config.get<string>('cliPath', 'tomo');

    try {
        const { stdout } = await execAsync(`${cliPath} ${args}`, {
            timeout: 10000,
            encoding: 'utf-8',
        });
        return stdout.trim();
    } catch (error) {
        console.error('Tomo CLI error:', error);
        return null;
    }
}

/**
 * Get pet state as a structured object.
 */
export async function getPetState(): Promise<PetState | null> {
    const raw = await execTomo('status');
    if (!raw) return null;

    // Parse basic info from status output
    const state: PetState = {
        name: 'Tomo',
        level: 1,
        stage: 'egg',
        mood: 'neutral',
        energy: 100,
        satiation: 100,
        affinity: 0,
        avatar: '🦊',
    };

    // Try to extract values from status text
    const levelMatch = raw.match(/lv\.(\d+)/);
    if (levelMatch) state.level = parseInt(levelMatch[1], 10);

    const energyMatch = raw.match(/Energy:\s*\S+\s*(\d+)\/100/);
    if (energyMatch) state.energy = parseInt(energyMatch[1], 10);

    const satMatch = raw.match(/Satiation:\s*\S+\s*(\d+)\/100/);
    if (satMatch) state.satiation = parseInt(satMatch[1], 10);

    const affinityMatch = raw.match(/亲密度.*\((\d+)\)/);
    if (affinityMatch) state.affinity = parseInt(affinityMatch[1], 10);

    const moodEmojis: Record<string, string> = {
        '⚡': 'energetic',
        '😊': 'happy',
        '😐': 'neutral',
        '😴': 'tired',
        '💀': 'exhausted',
    };
    for (const [emoji, mood] of Object.entries(moodEmojis)) {
        if (raw.includes(emoji)) {
            state.mood = mood;
            break;
        }
    }

    const stageMatch = raw.match(/Stage:\s*(\w+)/i);
    if (stageMatch) state.stage = stageMatch[1].toLowerCase();

    return state;
}

export interface PetState {
    name: string;
    level: number;
    stage: string;
    mood: string;
    energy: number;
    satiation: number;
    affinity: number;
    avatar: string;
}
