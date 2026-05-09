import { GameMode, LeaderboardItem } from "../api";

type LeaderboardMode = GameMode | "all";

type Props = {
  rows: LeaderboardItem[];
  loading: boolean;
  error: string;
  activeMode: LeaderboardMode;
  currentUserId?: number;
  isGroupContext?: boolean;
  onModeChange: (mode: LeaderboardMode) => void;
  onBack?: () => void;
};

const TABS: Array<{ value: LeaderboardMode; label: string }> = [
  { value: "all", label: "All" },
  { value: "peaceful", label: "Peaceful" },
  { value: "easy", label: "Easy" },
  { value: "normal", label: "Normal" },
  { value: "hard", label: "Hard" },
];

const MODE_LABELS: Record<string, string> = {
  peaceful: "Peaceful",
  easy: "Easy",
  normal: "Normal",
  hard: "Hard",
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function emptyText(mode: LeaderboardMode, isGroup: boolean): string {
  if (isGroup) return mode === "all" ? "No group scores yet." : `No group scores for ${MODE_LABELS[mode]} yet.`;
  if (mode === "all") return "Season 2 leaderboard is empty.";
  return `No scores for ${MODE_LABELS[mode]} yet.`;
}

function rankClass(rank: number): string {
  if (rank === 1) return "gold";
  if (rank === 2) return "silver";
  if (rank === 3) return "bronze";
  return "";
}

export function Leaderboard({
  rows,
  loading,
  error,
  activeMode,
  currentUserId,
  isGroupContext = false,
  onModeChange,
  onBack,
}: Props) {
  const visibleTabs = isGroupContext ? TABS.filter((t) => t.value !== "all") : TABS;
  const title = isGroupContext ? "Group Leaderboard" : "Season 2 Leaderboard";

  return (
    <section className={onBack ? "leaderboard-screen" : "leaderboard-panel"}>
      <div className="leaderboard-header">
        <h2>{title}</h2>
        <div className="leaderboard-tabs" role="tablist" aria-label="Leaderboard mode">
          {visibleTabs.map((tab) => (
            <button
              key={tab.value}
              className={`leaderboard-tab ${activeMode === tab.value ? "selected" : ""}`}
              onClick={() => onModeChange(tab.value)}
              role="tab"
              aria-selected={activeMode === tab.value}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="muted">Loading scores...</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && !error && rows.length === 0 && <p className="muted">{emptyText(activeMode, isGroupContext)}</p>}

      <div className="leaderboard-list">
        {rows.map((row) => {
          const isCurrent = currentUserId === row.user_id;
          return (
            <div
              className={`leaderboard-row ${rankClass(row.rank)} ${isCurrent ? "current-user" : ""}`}
              key={`${row.rank}-${row.user_id}-${row.mode}-${row.score}`}
            >
              <div className="leaderboard-rank">{row.rank}</div>
              <div className="leaderboard-player">
                <strong>{row.nickname.replace(/^@+/, "")}</strong>
                <span>{MODE_LABELS[row.mode] || row.mode} - {formatDate(row.created_at)}</span>
              </div>
              <div className="leaderboard-score">
                <strong>{row.score}</strong>
                <span>{row.lines} lines - Lv {row.level}</span>
              </div>
            </div>
          );
        })}
      </div>

      {onBack && <button className="menu-button menu-button-secondary" onClick={onBack}>Back</button>}
    </section>
  );
}
