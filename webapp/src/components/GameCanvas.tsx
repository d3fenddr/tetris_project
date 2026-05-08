import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { drawBoard, drawPreview } from "../game/renderer";
import { BOARD_COLS, BOARD_ROWS, GameSnapshot } from "../game/tetris";
import { RightControls } from "./RightControls";
import { GameAction } from "../game/tetris";

type Props = {
  snapshot: GameSnapshot;
  boardRef: RefObject<HTMLDivElement>;
  accountName: string;
  saveStatus: string;
  startHold: (action: GameAction) => void;
  stopHold: () => void;
  tap: (action: GameAction) => void;
  onRestart: () => void;
  onChangeMode: () => void;
  onMainMenu: () => void;
  onLeaderboard: () => void;
};

export function GameCanvas({
  snapshot,
  boardRef,
  accountName,
  saveStatus,
  startHold,
  stopHold,
  tap,
  onRestart,
  onChangeMode,
  onMainMenu,
  onLeaderboard,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const previewRef = useRef<HTMLCanvasElement | null>(null);
  const [resizeVersion, setResizeVersion] = useState(0);

  useLayoutEffect(() => {
    const canvases = [canvasRef.current, previewRef.current].filter(Boolean) as HTMLCanvasElement[];
    if (!canvases.length) return;

    const resizeCanvas = (canvas: HTMLCanvasElement) => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(1, Math.round(rect.width * dpr));
      const height = Math.max(1, Math.round(rect.height * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
    };

    const observer = new ResizeObserver(() => {
      canvases.forEach(resizeCanvas);
      setResizeVersion((value) => value + 1);
    });

    canvases.forEach((canvas) => {
      resizeCanvas(canvas);
      observer.observe(canvas);
    });
    setResizeVersion((value) => value + 1);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    drawBoard(canvas, snapshot);
  }, [snapshot, resizeVersion]);

  useEffect(() => {
    const canvas = previewRef.current;
    if (!canvas) return;
    drawPreview(canvas, snapshot.next.shape, snapshot.next.color);
  }, [snapshot.next, resizeVersion]);

  return (
    <section className="game-screen">
      <header className="game-hud">
        <div><span>Score</span><strong>{snapshot.score}</strong></div>
        <div><span>Lines</span><strong>{snapshot.lines}</strong></div>
        <div><span>Combo</span><strong>{snapshot.combo ? `x${snapshot.combo}` : "-"}</strong></div>
        <div><span>Mode</span><strong>{snapshot.mode}</strong></div>
      </header>
      <div className="play-area" ref={boardRef}>
        <div className="board-frame">
          <canvas
            ref={canvasRef}
            className="game-canvas"
            width={BOARD_COLS * 32}
            height={BOARD_ROWS * 32}
            aria-label="Tetris board"
          />
          {snapshot.lastClear && (
            <div className="score-pop" key={snapshot.lastClear.id}>
              +{snapshot.lastClear.points}
              {snapshot.lastClear.combo >= 2 && <span>COMBO x{snapshot.lastClear.combo}</span>}
            </div>
          )}
          {snapshot.status !== "playing" && (
            <div className="board-overlay">
              <strong>{snapshot.status === "game_over" ? "Game over" : snapshot.status === "paused" ? "Paused" : "Ready"}</strong>
              <span>{snapshot.status === "paused" ? "Tap Resume to continue" : "Choose Restart to play"}</span>
            </div>
          )}
        </div>
        <RightControls
          disabled={snapshot.status !== "playing"}
          paused={snapshot.status === "paused"}
          startHold={startHold}
          stopHold={stopHold}
          tap={tap}
        />
      </div>
      <aside className="side-panel">
        <div>
          <span>Next</span>
          <canvas ref={previewRef} className="next-canvas" width={120} height={100} />
        </div>
        <div className="stat-row"><span>Score</span><strong>{snapshot.score}</strong></div>
        <div className="stat-row"><span>Lines</span><strong>{snapshot.lines}</strong></div>
        <div className="stat-row"><span>Level</span><strong>{snapshot.level}</strong></div>
        <div className="stat-row"><span>Player</span><strong>{accountName}</strong></div>
      </aside>
      {snapshot.status === "game_over" && (
        <div className="game-over-panel">
          <h2>Final Score {snapshot.score}</h2>
          <p>{snapshot.mode} - {snapshot.lines} lines</p>
          {saveStatus && <strong>{saveStatus}</strong>}
          <div className="game-over-actions">
            <button onClick={onRestart}>Restart</button>
            <button onClick={onChangeMode}>Change Mode</button>
            <button onClick={onMainMenu}>Main Menu</button>
            <button onClick={onLeaderboard}>Leaderboard</button>
          </div>
        </div>
      )}
    </section>
  );
}
