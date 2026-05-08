export type Cell = string | null;
export type Matrix = number[][];
export type GameStatus = "ready" | "playing" | "paused" | "game_over";
export type GameAction = "left" | "right" | "down" | "rotate" | "hardDrop" | "pause" | "restart";
export type GameMode = "peaceful" | "easy" | "normal" | "hard";

export type ActivePiece = {
  shape: Matrix;
  color: string;
  x: number;
  y: number;
};

export type GameSnapshot = {
  board: Cell[][];
  active: ActivePiece | null;
  next: ActivePiece;
  score: number;
  lines: number;
  level: number;
  combo: number;
  mode: GameMode;
  status: GameStatus;
  lastClear: ClearEvent | null;
};

export type ClearEvent = {
  id: number;
  lines: number;
  points: number;
  combo: number;
  rows: number[];
};

const COLS = 10;
const ROWS = 20;
const FALL_SPEED_BASE_MS = 1000;
const FALL_SPEED_SCORE_STEP = 500;
const FALL_SPEED_DECREASE_MS = 80;
const FALL_SPEED_MIN_MS = 160;
const HARD_DROP_SCORE_PER_ROW = 2;

export const GAME_MODES: Array<{ value: GameMode; label: string; description: string }> = [
  { value: "peaceful", label: "Peaceful", description: "The 88 piece is disabled." },
  { value: "easy", label: "Easy", description: "The 88 piece appears rarely." },
  { value: "normal", label: "Normal", description: "The 88 piece appears more often." },
  { value: "hard", label: "Hard", description: "The 88 piece appears very often." },
];

// Copied from the desktop pygame config: T, O, Z, S, I, 88, L, J.
const PIECES: Array<{ name: string; shape: Matrix; color: string }> = [
  { name: "T", shape: [[1, 1, 1], [0, 1, 0]], color: "#be82ff" },
  { name: "O", shape: [[1, 1], [1, 1]], color: "#ffdd5b" },
  { name: "Z", shape: [[0, 1, 1], [1, 1, 0]], color: "#5c5cff" },
  { name: "S", shape: [[1, 1, 0], [0, 1, 1]], color: "#ff583b" },
  { name: "I", shape: [[1, 1, 1, 1]], color: "#58beff" },
  { shape: [
        [1, 0, 1, 1, 1],
        [1, 0, 1, 0, 0],
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 1],
        [1, 1, 1, 0, 1],], name: "88", color: "#800000" },
  { name: "L", shape: [[1, 0], [1, 0], [1, 1]], color: "#ff9a52" },
  { name: "J", shape: [[0, 1], [0, 1], [1, 1]], color: "#5effa8" },
];

const MODE_WEIGHTS: Record<GameMode, Record<string, number>> = {
  peaceful: { "88": 0 },
  easy: { "88": 17.5 },
  normal: { "88": 35 },
  hard: { "88": 200 },
};

function emptyBoard(): Cell[][] {
  return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => null));
}

function cloneBoard(board: Cell[][]): Cell[][] {
  return board.map((row) => [...row]);
}

function clonePiece(piece: ActivePiece): ActivePiece {
  return { ...piece, shape: piece.shape.map((row) => [...row]) };
}

function randomPiece(mode: GameMode): ActivePiece {
  const weights = PIECES.map((piece) => MODE_WEIGHTS[mode][piece.name] ?? 100);
  const total = weights.reduce((sum, value) => sum + value, 0);
  let roll = Math.random() * total;
  const template = PIECES.find((_piece, index) => {
    roll -= weights[index];
    return roll < 0;
  }) ?? PIECES[0];
  return {
    shape: template.shape.map((row) => [...row]),
    color: template.color,
    x: Math.floor(COLS / 2) - Math.ceil(template.shape[0].length / 2),
    y: 0,
  };
}

function rotateMatrix(shape: Matrix): Matrix {
  return shape[0].map((_, col) => shape.map((row) => row[col]).reverse());
}

export class TetrisGame {
  private board: Cell[][] = emptyBoard();
  private active: ActivePiece | null = null;
  private modeValue: GameMode = "normal";
  private nextPiece: ActivePiece = randomPiece(this.modeValue);
  private scoreValue = 0;
  private linesValue = 0;
  private levelValue = 1;
  private comboValue = 0;
  private statusValue: GameStatus = "ready";
  private dropAccumulator = 0;
  private clearEventId = 0;
  private lastClearValue: ClearEvent | null = null;

  start(mode: GameMode = this.modeValue): void {
    this.modeValue = mode;
    this.board = emptyBoard();
    this.scoreValue = 0;
    this.linesValue = 0;
    this.levelValue = 1;
    this.comboValue = 0;
    this.statusValue = "playing";
    this.dropAccumulator = 0;
    this.lastClearValue = null;
    this.nextPiece = randomPiece(this.modeValue);
    this.spawnPiece();
  }

  togglePause(): void {
    if (this.statusValue === "playing") {
      this.statusValue = "paused";
    } else if (this.statusValue === "paused") {
      this.statusValue = "playing";
    }
  }

  tick(deltaMs: number): boolean {
    if (this.statusValue !== "playing") return false;
    this.dropAccumulator += deltaMs;
    if (this.dropAccumulator < this.dropInterval()) return false;
    this.dropAccumulator = 0;
    return this.softDrop();
  }

  move(dx: number): boolean {
    if (!this.active || this.statusValue !== "playing") return false;
    const moved = { ...this.active, x: this.active.x + dx };
    if (this.collides(moved)) return false;
    this.active = moved;
    return true;
  }

  softDrop(): boolean {
    if (!this.active || this.statusValue !== "playing") return false;
    const moved = { ...this.active, y: this.active.y + 1 };
    if (!this.collides(moved)) {
      this.active = moved;
      return true;
    }
    this.lockPiece();
    return true;
  }

  rotate(): boolean {
    if (!this.active || this.statusValue !== "playing") return false;
    const rotated = { ...this.active, shape: rotateMatrix(this.active.shape) };
    for (const offset of [0, -1, 1, -2, 2]) {
      const candidate = { ...rotated, x: rotated.x + offset };
      if (!this.collides(candidate)) {
        this.active = candidate;
        return true;
      }
    }
    return false;
  }

  hardDrop(): boolean {
    if (!this.active || this.statusValue !== "playing") return false;
    let dropped = 0;
    while (this.active && !this.collides({ ...this.active, y: this.active.y + 1 })) {
      this.active = { ...this.active, y: this.active.y + 1 };
      dropped += 1;
    }
    this.scoreValue += dropped * HARD_DROP_SCORE_PER_ROW;
    this.lockPiece();
    return true;
  }

  action(action: GameAction): boolean {
    if (action === "left") return this.move(-1);
    if (action === "right") return this.move(1);
    if (action === "down") return this.softDrop();
    if (action === "rotate") return this.rotate();
    if (action === "hardDrop") return this.hardDrop();
    if (action === "pause") {
      this.togglePause();
      return true;
    }
    if (action === "restart") {
      this.start();
      return true;
    }
    return false;
  }

  snapshot(): GameSnapshot {
    return {
      board: cloneBoard(this.board),
      active: this.active ? clonePiece(this.active) : null,
      next: clonePiece(this.nextPiece),
      score: this.scoreValue,
      lines: this.linesValue,
      level: this.levelValue,
      combo: this.comboValue,
      mode: this.modeValue,
      status: this.statusValue,
      lastClear: this.lastClearValue ? { ...this.lastClearValue, rows: [...this.lastClearValue.rows] } : null,
    };
  }

  private dropInterval(): number {
    return Math.max(FALL_SPEED_MIN_MS, FALL_SPEED_BASE_MS - (this.levelValue - 1) * FALL_SPEED_DECREASE_MS);
  }

  private updateLevel(): void {
    this.levelValue = Math.max(1, Math.floor(this.scoreValue / FALL_SPEED_SCORE_STEP) + 1);
  }

  private spawnPiece(): void {
    this.active = clonePiece(this.nextPiece);
    this.nextPiece = randomPiece(this.modeValue);
    if (this.active && this.collides(this.active)) {
      this.active = null;
      this.statusValue = "game_over";
    }
  }

  private collides(piece: ActivePiece): boolean {
    for (let y = 0; y < piece.shape.length; y += 1) {
      for (let x = 0; x < piece.shape[y].length; x += 1) {
        if (!piece.shape[y][x]) continue;
        const boardX = piece.x + x;
        const boardY = piece.y + y;
        if (boardX < 0 || boardX >= COLS || boardY >= ROWS) return true;
        if (boardY >= 0 && this.board[boardY][boardX]) return true;
      }
    }
    return false;
  }

  private lockPiece(): void {
    if (!this.active) return;
    for (let y = 0; y < this.active.shape.length; y += 1) {
      for (let x = 0; x < this.active.shape[y].length; x += 1) {
        if (!this.active.shape[y][x]) continue;
        const boardY = this.active.y + y;
        const boardX = this.active.x + x;
        if (boardY < 0) {
          this.statusValue = "game_over";
          this.active = null;
          return;
        }
        this.board[boardY][boardX] = this.active.color;
      }
    }
    this.clearLines();
    this.spawnPiece();
  }

  private clearLines(): void {
    const clearedRows: number[] = [];
    const remaining = this.board.filter((row, index) => {
      const keep = row.some((cell) => !cell);
      if (!keep) clearedRows.push(index);
      return keep;
    });
    const cleared = ROWS - remaining.length;
    if (cleared === 0) {
      this.comboValue = 0;
      this.lastClearValue = null;
      return;
    }
    const newRows = Array.from({ length: cleared }, () => Array.from({ length: COLS }, () => null));
    this.board = [...newRows, ...remaining];
    this.linesValue += cleared;
    this.comboValue += 1;
    const points = cleared * 100 * this.comboValue;
    this.scoreValue += points;
    this.updateLevel();
    this.clearEventId += 1;
    this.lastClearValue = { id: this.clearEventId, lines: cleared, points, combo: this.comboValue, rows: clearedRows };
  }
}

export const BOARD_COLS = COLS;
export const BOARD_ROWS = ROWS;
