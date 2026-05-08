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

  const rotateProps = {
    "data-control-button": true,
    disabled,
    onPointerDown: (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      tap("rotate");
    },
  };

  return (
    <section className="mobile-dpad-panel" aria-label="Game controls">
      <button className="dpad-button dpad-up" aria-label="Rotate piece" {...rotateProps}>
        <span aria-hidden="true">&#8635;</span>
      </button>
      <button className="dpad-button dpad-left" aria-label="Move left" {...holdProps("left")}>
        <span aria-hidden="true">&larr;</span>
      </button>
      <div className="dpad-hub" aria-hidden="true" />
      <button className="dpad-button dpad-right" aria-label="Move right" {...holdProps("right")}>
        <span aria-hidden="true">&rarr;</span>
      </button>
      <button className="dpad-button dpad-down" aria-label="Move down" {...holdProps("down")}>
        <span aria-hidden="true">&darr;</span>
      </button>
    </section>
  );
}
