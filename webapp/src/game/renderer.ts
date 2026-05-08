import { BOARD_COLS, BOARD_ROWS, Cell, GameSnapshot, Matrix } from "./tetris";

const GRID_COLOR = "rgba(164, 210, 255, 0.07)";
const EMPTY_COLOR = "#091018";
const EMPTY_CELL_COLOR = "#0d1621";

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
  const maxDimension = Math.max(shape[0].length, shape.length);
  const size = Math.floor(Math.min(width / (maxDimension + 0.8), height / (maxDimension + 0.8)));
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
    context.fillStyle = EMPTY_CELL_COLOR;
    context.fillRect(x + 0.5, y + 0.5, size - 1, size - 1);
    return;
  }
  const inset = Math.max(1.2, size * 0.055);
  const radius = Math.max(2, size * 0.11);
  const innerX = x + inset;
  const innerY = y + inset;
  const innerSize = size - inset * 2;
  context.save();
  context.shadowColor = "rgba(0,0,0,0.32)";
  context.shadowBlur = Math.max(2, size * 0.12);
  context.shadowOffsetY = 1;
  roundedRect(context, innerX, innerY, innerSize, innerSize, radius);
  context.fillStyle = color;
  context.fill();
  context.shadowColor = "transparent";
  context.fillStyle = "rgba(255,255,255,0.2)";
  roundedRect(context, innerX + 1, innerY + 1, innerSize - 2, Math.max(2, innerSize * 0.22), radius * 0.65);
  context.fill();
  context.strokeStyle = "rgba(255,255,255,0.12)";
  context.lineWidth = 1;
  roundedRect(context, innerX + 0.5, innerY + 0.5, innerSize - 1, innerSize - 1, radius);
  context.stroke();
  context.strokeStyle = "rgba(0,0,0,0.32)";
  roundedRect(context, innerX, innerY, innerSize, innerSize, radius);
  context.stroke();
  context.restore();
}

function roundedRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
): void {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + safeRadius, y);
  context.lineTo(x + width - safeRadius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  context.lineTo(x + width, y + height - safeRadius);
  context.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  context.lineTo(x + safeRadius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  context.lineTo(x, y + safeRadius);
  context.quadraticCurveTo(x, y, x + safeRadius, y);
  context.closePath();
}
