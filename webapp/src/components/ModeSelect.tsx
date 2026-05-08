import { GameMode, GAME_MODES } from "../game/tetris";

type Props = {
  selected: GameMode;
  onSelect: (mode: GameMode) => void;
  onBack: () => void;
};

export function ModeSelect({ selected, onSelect, onBack }: Props) {
  return (
    <section className="menu-screen">
      <div className="mode-panel">
        <h1>Choose Mode</h1>
        <div className="mode-list">
          {GAME_MODES.map((mode) => (
            <button
              key={mode.value}
              className={`mode-card ${selected === mode.value ? "selected" : ""}`}
              onClick={() => onSelect(mode.value)}
            >
              <strong>{mode.label}</strong>
              <span>{mode.description}</span>
            </button>
          ))}
        </div>
        <button className="menu-button menu-button-secondary" onClick={onBack}>Back</button>
      </div>
    </section>
  );
}
