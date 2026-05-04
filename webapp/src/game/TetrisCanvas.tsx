import { useEffect, useRef } from "react";

type Control = "left" | "right" | "rotate" | "soft_drop" | "hard_drop" | null;

type Props = {
  onScore: (score: number) => void;
  externalControl: Control;
};

const COLS = 10;
const ROWS = 20;
const CELL_SIZE = 16;
const CANVAS_WIDTH = COLS * CELL_SIZE;
const CANVAS_HEIGHT = ROWS * CELL_SIZE;

export function TetrisCanvas({ onScore, externalControl }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pieceX = useRef(4);
  const pieceY = useRef(0);
  const score = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const draw = () => {
      context.fillStyle = "#121212";
      context.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      context.strokeStyle = "#393939";
      for (let y = 0; y <= ROWS; y += 1) {
        context.beginPath();
        context.moveTo(0, y * CELL_SIZE);
        context.lineTo(CANVAS_WIDTH, y * CELL_SIZE);
        context.stroke();
      }
      for (let x = 0; x <= COLS; x += 1) {
        context.beginPath();
        context.moveTo(x * CELL_SIZE, 0);
        context.lineTo(x * CELL_SIZE, CANVAS_HEIGHT);
        context.stroke();
      }

      context.fillStyle = "#c43d22";
      context.fillRect(pieceX.current * CELL_SIZE, pieceY.current * CELL_SIZE, CELL_SIZE, CELL_SIZE);
    };

    const interval = window.setInterval(() => {
      pieceY.current += 1;
      if (pieceY.current >= ROWS) {
        pieceY.current = 0;
        pieceX.current = Math.max(0, Math.min(COLS - 1, pieceX.current));
        score.current += 10;
        onScore(score.current);
      }
      draw();
    }, 400);

    draw();
    return () => window.clearInterval(interval);
  }, [onScore]);

  useEffect(() => {
    if (!externalControl) return;
    if (externalControl === "left") pieceX.current = Math.max(0, pieceX.current - 1);
    if (externalControl === "right") pieceX.current = Math.min(COLS - 1, pieceX.current + 1);
    if (externalControl === "soft_drop") pieceY.current = Math.min(ROWS - 1, pieceY.current + 1);
    if (externalControl === "hard_drop") pieceY.current = ROWS - 1;
    if (externalControl === "rotate") {
      score.current += 1;
      onScore(score.current);
    }
  }, [externalControl, onScore]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") pieceX.current = Math.max(0, pieceX.current - 1);
      if (event.key === "ArrowRight") pieceX.current = Math.min(COLS - 1, pieceX.current + 1);
      if (event.key === "ArrowDown") pieceY.current = Math.min(ROWS - 1, pieceY.current + 1);
      if (event.key === "ArrowUp" || event.key.toLowerCase() === "x") {
        score.current += 1;
        onScore(score.current);
      }
      if (event.key === " ") pieceY.current = ROWS - 1;
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onScore]);

  return (
    <div className="canvas-wrap">
      <canvas ref={canvasRef} width={CANVAS_WIDTH} height={CANVAS_HEIGHT} />
    </div>
  );
}

