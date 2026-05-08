import { LeaderboardItem } from "../api";

type Props = {
  rows: LeaderboardItem[];
  loading: boolean;
  error: string;
  onBack?: () => void;
};

export function Leaderboard({ rows, loading, error, onBack }: Props) {
  return (
    <section className={onBack ? "leaderboard-screen" : "leaderboard-panel"}>
      <h2>Leaderboard</h2>
      {loading && <p className="muted">Loading scores...</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && !error && rows.length === 0 && <p className="muted">No scores yet.</p>}
      <div className="leaderboard-list">
        {rows.map((row) => (
          <div className="leaderboard-row" key={`${row.rank}-${row.nickname}-${row.score}`}>
            <span>{row.rank}. {row.nickname.replace(/^@+/, "")}</span>
            <strong>{row.score}</strong>
          </div>
        ))}
      </div>
      {onBack && <button className="menu-button menu-button-secondary" onClick={onBack}>Back</button>}
    </section>
  );
}
