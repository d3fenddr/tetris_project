import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { drawBoard, drawPreview } from "../game/renderer";
import { BOARD_COLS, BOARD_ROWS, GameAction, GameSnapshot } from "../game/tetris";
import { MobileDPadControls } from "./MobileDPadControls";

type Props = {
  snapshot: GameSnapshot;
  boardRef: RefObject<HTMLDivElement>;
  bestText: string;
  saveStatus: string;
  soundEnabled: boolean;
  startHold: (action: GameAction) => void;
  stopHold: () => void;
  tap: (action: GameAction) => void;
  onToggleSound: () => void;
  onRestart: () => void;
  onChangeMode: () => void;
  onMainMenu: () => void;
  onLeaderboard: () => void;
};

export function GameCanvas({
  snapshot,
  boardRef,
  bestText,
  saveStatus,
  soundEnabled,
  startHold,
  stopHold,
  tap,
  onToggleSound,
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
      <button
        className="game-pause-button"
        data-control-button
        onPointerDown={() => tap("pause")}
        disabled={snapshot.status === "game_over"}
        aria-label="Pause game"
      >
        <span aria-hidden="true">II</span>
      </button>
      <header className="game-hud">
        <div className="hud-card hud-main">
          <div className="hud-score-main">
            <span>Score</span>
            <strong>{snapshot.score}</strong>
          </div>
          <div className="hud-meta">
            <span>Mode</span>
            <strong>{snapshot.mode}</strong>
            <small>Level {snapshot.level}</small>
            <small>Best: {bestText}</small>
          </div>
        </div>
        <div className="hud-card next-preview-card">
          <span>Next</span>
          <canvas ref={previewRef} className="next-canvas" width={120} height={100} />
        </div>
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
            <div className={`board-overlay ${snapshot.status === "paused" ? "pause-overlay" : ""}`}>
              {snapshot.status === "paused" ? (
                <div className="pause-menu" role="dialog" aria-label="Pause menu">
                  <strong>Paused</strong>
                  <button onPointerDown={() => tap("pause")}>Continue</button>
                  <button onPointerDown={onToggleSound}>Music: {soundEnabled ? "On" : "Off"}</button>
                  <button onPointerDown={onRestart}>Restart</button>
                  <button onPointerDown={onMainMenu}>Exit</button>
                </div>
              ) : (
                <>
                  <strong>{snapshot.status === "game_over" ? "Game over" : "Ready"}</strong>
                  <span>Choose Restart to play</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>
      <MobileDPadControls
        disabled={snapshot.status !== "playing"}
        startHold={startHold}
        stopHold={stopHold}
        tap={tap}
      />
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
