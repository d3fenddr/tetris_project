import { BOARD_COLS, BOARD_ROWS, Cell, GameSnapshot, Matrix } from "./tetris";

const GRID_COLOR = "rgba(255,255,255,0.08)";
const EMPTY_COLOR = "#0b1118";

export function drawBoard(canvas: HTMLCanvasElement, snapshot: GameSnapshot): void {
  const context = canvas.getContext("2d");
  if (!context) return;

  const dpr = window.devicePixelRatio || 1;
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  const cellSize = width / BOARD_COLS;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);
  context.fillStyle = EMPTY_COLOR;
  context.fillRect(0, 0, width, height);

  const displayBoard: Cell[][] = snapshot.board.map((row) => [...row]);
  if (snapshot.active) {
    snapshot.active.shape.forEach((row, y) => {
      row.forEach((filled, x) => {
        if (!filled) return;
        const boardX = snapshot.active!.x + x;
        const boardY = snapshot.active!.y + y;
        if (boardY >= 0 && boardY < BOARD_ROWS && boardX >= 0 && boardX < BOARD_COLS) {
          displayBoard[boardY][boardX] = snapshot.active!.color;
        }
      });
    });
  }

  displayBoard.forEach((row, y) => {
    row.forEach((cell, x) => {
      drawCell(context, x * cellSize, y * cellSize, cellSize, cell);
    });
  });

  if (snapshot.lastClear) {
    context.save();
    context.fillStyle = "rgba(255, 210, 94, 0.26)";
    context.shadowColor = "rgba(255, 210, 94, 0.85)";
    context.shadowBlur = 14;
    snapshot.lastClear.rows.forEach((row) => {
      context.fillRect(0, row * cellSize, width, cellSize);
    });
    context.restore();
  }

  context.strokeStyle = GRID_COLOR;
  context.lineWidth = 1;
  for (let x = 0; x <= BOARD_COLS; x += 1) {
    context.beginPath();
    context.moveTo(x * cellSize, 0);
    context.lineTo(x * cellSize, height);
    context.stroke();
  }
  for (let y = 0; y <= BOARD_ROWS; y += 1) {
    context.beginPath();
    context.moveTo(0, y * cellSize);
    context.lineTo(width, y * cellSize);
    context.stroke();
  }
}

export function drawPreview(canvas: HTMLCanvasElement, shape: Matrix, color: string): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);
  context.fillStyle = "rgba(0,0,0,0.28)";
  context.fillRect(0, 0, width, height);
  const size = Math.floor(Math.min(width / 5, height / 5));
  const offsetX = Math.floor((width - shape[0].length * size) / 2);
  const offsetY = Math.floor((height - shape.length * size) / 2);
  shape.forEach((row, y) => {
    row.forEach((filled, x) => {
      if (filled) drawCell(context, offsetX + x * size, offsetY + y * size, size, color);
    });
  });
}

function drawCell(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: string | null,
): void {
  if (!color) {
    context.fillStyle = EMPTY_COLOR;
    context.fillRect(x, y, size, size);
    return;
  }
  context.fillStyle = color;
  context.fillRect(x + 1, y + 1, size - 2, size - 2);
  context.fillStyle = "rgba(255,255,255,0.2)";
  context.fillRect(x + 2, y + 2, size - 4, Math.max(2, size * 0.18));
  context.strokeStyle = "rgba(0,0,0,0.35)";
  context.strokeRect(x + 1, y + 1, size - 2, size - 2);
}
