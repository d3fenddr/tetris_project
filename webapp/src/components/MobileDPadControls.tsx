import type { PointerEvent } from "react";
import { GameAction } from "../game/tetris";

type Props = {
  disabled: boolean;
  startHold: (action: GameAction) => void;
  stopHold: () => void;
  tap: (action: GameAction) => void;
};

type HoldAction = "left" | "right" | "down";

export function MobileDPadControls({ disabled, startHold, stopHold, tap }: Props) {
  const holdProps = (action: HoldAction) => ({
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

  const tapProps = (action: GameAction) => ({
    "data-control-button": true,
    disabled,
    onPointerDown: (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      tap(action);
    },
  });

  return (
    <section className="mobile-controls" aria-label="Game controls">
      <div className="controls-joystick">
        <div className="dpad" role="group" aria-label="Joystick controls">
          <button className="ctrl-btn ctrl-up ctrl-rotate" aria-label="Rotate" {...tapProps("rotate")}>
            <span aria-hidden="true">&uarr;</span>
          </button>
          <div className="dpad-row">
            <button className="ctrl-btn ctrl-left" aria-label="Move left" {...holdProps("left")}>
              <span aria-hidden="true">&larr;</span>
            </button>
            <button className="ctrl-btn ctrl-down" aria-label="Soft drop" {...holdProps("down")}>
              <span aria-hidden="true">&darr;</span>
            </button>
            <button className="ctrl-btn ctrl-right" aria-label="Move right" {...holdProps("right")}>
              <span aria-hidden="true">&rarr;</span>
            </button>
          </div>
        </div>
        <button
          className="ctrl-btn ctrl-harddrop ctrl-harddrop-standalone"
          aria-label="Hard drop"
          {...tapProps("hardDrop")}
        >
          <span aria-hidden="true">DROP</span>
        </button>
      </div>
    </section>
  );
}
