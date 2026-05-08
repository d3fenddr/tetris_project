import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import { GameAction } from "./game/tetris";

type ControlsOptions = {
  enabled: boolean;
  boardRef: RefObject<HTMLElement>;
  onAction: (action: GameAction) => void;
};

const REPEATABLE_WITH_ROTATE = new Set<GameAction>(["left", "right", "down", "rotate"]);
const INITIAL_DELAY = 145;
const MOVE_REPEAT_INTERVAL = 65;
const DOWN_REPEAT_INTERVAL = 45;
const ROTATE_REPEAT_INTERVAL = 150;
const SWIPE_MIN_DISTANCE = 32;

function intervalForAction(action: GameAction): number {
  if (action === "down") return DOWN_REPEAT_INTERVAL;
  if (action === "rotate") return ROTATE_REPEAT_INTERVAL;
  return MOVE_REPEAT_INTERVAL;
}

export function useGameControls({ enabled, boardRef, onAction }: ControlsOptions) {
  const holdRef = useRef<{ action: GameAction | null; delayId?: number; intervalId?: number }>({ action: null });
  const swipeStart = useRef<{ x: number; y: number; target: EventTarget | null } | null>(null);
  const actionRef = useRef(onAction);
  actionRef.current = onAction;

  const stopHold = () => {
    const hold = holdRef.current;
    if (hold.delayId) window.clearTimeout(hold.delayId);
    if (hold.intervalId) window.clearInterval(hold.intervalId);
    holdRef.current = { action: null };
  };

  const startHold = (action: GameAction) => {
    if (!enabled) return;
    stopHold();
    actionRef.current(action);
    if (!REPEATABLE_WITH_ROTATE.has(action)) return;
    const delayId = window.setTimeout(() => {
      const intervalId = window.setInterval(() => actionRef.current(action), intervalForAction(action));
      holdRef.current = { action, intervalId };
    }, INITIAL_DELAY);
    holdRef.current = { action, delayId };
  };

  useEffect(() => {
    const keyDown = (event: KeyboardEvent) => {
      const key = event.key;
      if (["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp", " "].includes(key)) {
        event.preventDefault();
      }
      if (!enabled) return;
      if (key === "ArrowLeft" && !event.repeat) startHold("left");
      if (key === "ArrowRight" && !event.repeat) startHold("right");
      if (key === "ArrowDown" && !event.repeat) startHold("down");
      if (key === "ArrowUp" && !event.repeat) startHold("rotate");
      if (key === " " && !event.repeat) actionRef.current("hardDrop");
      if (key === "Escape" || key === "Enter") actionRef.current("pause");
    };
    const keyUp = (event: KeyboardEvent) => {
      if (["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp"].includes(event.key)) stopHold();
    };
    window.addEventListener("keydown", keyDown, { passive: false });
    window.addEventListener("keyup", keyUp);
    window.addEventListener("blur", stopHold);
    const stopOnVisibility = () => {
      if (document.hidden) stopHold();
    };
    document.addEventListener("visibilitychange", stopOnVisibility);
    window.addEventListener("mouseup", stopHold);
    window.addEventListener("touchend", stopHold, { passive: true });
    return () => {
      window.removeEventListener("keydown", keyDown);
      window.removeEventListener("keyup", keyUp);
      window.removeEventListener("blur", stopHold);
      document.removeEventListener("visibilitychange", stopOnVisibility);
      window.removeEventListener("mouseup", stopHold);
      window.removeEventListener("touchend", stopHold);
      stopHold();
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled) stopHold();
  }, [enabled]);

  useEffect(() => {
    const board = boardRef.current;
    if (!board) return;
    const pointerDown = (event: PointerEvent) => {
      if ((event.target as HTMLElement).closest("[data-control-button]")) return;
      swipeStart.current = { x: event.clientX, y: event.clientY, target: event.target };
    };
    const pointerUp = (event: PointerEvent) => {
      const start = swipeStart.current;
      swipeStart.current = null;
      if (!enabled || !start) return;
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < SWIPE_MIN_DISTANCE) return;
      if (Math.abs(dx) > Math.abs(dy)) {
        actionRef.current(dx > 0 ? "right" : "left");
      } else {
        actionRef.current(dy > 0 ? "down" : "rotate");
      }
    };
    const cancel = () => {
      swipeStart.current = null;
    };
    board.addEventListener("pointerdown", pointerDown);
    board.addEventListener("pointerup", pointerUp);
    board.addEventListener("pointercancel", cancel);
    board.addEventListener("pointerleave", cancel);
    return () => {
      board.removeEventListener("pointerdown", pointerDown);
      board.removeEventListener("pointerup", pointerUp);
      board.removeEventListener("pointercancel", cancel);
      board.removeEventListener("pointerleave", cancel);
    };
  }, [boardRef, enabled]);

  return { startHold, stopHold, stopAllHolds: stopHold };
}
