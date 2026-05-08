import type { PointerEvent } from "react";
import { GameAction } from "../game/tetris";

type Props = {
  disabled: boolean;
  paused: boolean;
  startHold: (action: GameAction) => void;
  stopHold: () => void;
  tap: (action: GameAction) => void;
};

export function RightControls({ disabled, paused, startHold, stopHold, tap }: Props) {
  const holdProps = (action: GameAction) => ({
    "data-control-button": true,
    disabled,
    onPointerDown: (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      startHold(action);
    },
    onPointerUp: stopHold,
    onPointerCancel: stopHold,
    onPointerLeave: stopHold,
    onLostPointerCapture: stopHold,
  });

  return (
    <section className="right-controls" aria-label="Game controls">
      <button className="control control-rotate" {...holdProps("rotate")}>Rotate</button>
      <div className="control-row">
        <button className="control" {...holdProps("left")}>Left</button>
        <button className="control" {...holdProps("right")}>Right</button>
      </div>
      <button className="control control-down" {...holdProps("down")}>Down</button>
      <button className="control control-pause" data-control-button onPointerDown={() => tap("pause")}>
        {paused ? "Resume" : "Pause"}
      </button>
    </section>
  );
}
