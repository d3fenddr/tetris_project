type Props = {
  enabled: boolean;
  onToggle: () => void;
};

export function SoundToggle({ enabled, onToggle }: Props) {
  return (
    <button className="menu-button menu-button-secondary" onClick={onToggle}>
      Sound {enabled ? "On" : "Off"}
    </button>
  );
}
