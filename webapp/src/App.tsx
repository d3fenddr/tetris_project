import { useMemo, useState } from "react";
import { TetrisCanvas } from "./game/TetrisCanvas";

type Control = "left" | "right" | "rotate" | "soft_drop" | "hard_drop";

export function App() {
  const [score, setScore] = useState(0);
  const [lastControl, setLastControl] = useState<Control | null>(null);

  const controls = useMemo(
    () => [
      { id: "left" as const, label: "Left" },
      { id: "right" as const, label: "Right" },
      { id: "rotate" as const, label: "Rotate" },
      { id: "soft_drop" as const, label: "Soft Drop" },
      { id: "hard_drop" as const, label: "Hard Drop" },
    ],
    [],
  );

  return (
    <main className="app-shell">
      <header className="app-header">
        <h1>Tetris</h1>
        <p>Telegram Mini App scaffold</p>
      </header>

      <section className="score-card">
        <span>Score</span>
        <strong>{score}</strong>
      </section>

      <TetrisCanvas
        onScore={setScore}
        externalControl={lastControl}
      />

      <section className="controls-grid">
        {controls.map((control) => (
          <button
            key={control.id}
            className="control-btn"
            onTouchStart={() => setLastControl(control.id)}
            onMouseDown={() => setLastControl(control.id)}
          >
            {control.label}
          </button>
        ))}
      </section>
    </main>
  );
}

