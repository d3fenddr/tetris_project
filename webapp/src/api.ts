const API_BASE = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

export type AuthUser = {
  id: number;
  nickname: string;
  games_played: number;
  best_score: number;
};

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
};

export type LeaderboardItem = {
  rank: number;
  nickname: string;
  score: number;
  lines: number;
  level: number;
  mode: string;
};

export type GameMode = "peaceful" | "easy" | "normal" | "hard";

function cleanNickname(value: string): string {
  const clean = value.trim().replace(/^@+/, "");
  return clean || "unknown";
}

function mapSession(payload: any): AuthSession {
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    user: { ...payload.user, nickname: cleanNickname(payload.user?.nickname || "") },
  };
}

export async function authenticateTelegram(initData: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE}/telegram/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });
  if (!response.ok) throw new Error("Telegram authentication failed");
  return mapSession(await response.json());
}

export async function loginWithPassword(nickname: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname, password }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Login failed");
  }
  return mapSession(await response.json());
}

export async function fetchLeaderboard(mode: GameMode | "all" = "normal"): Promise<LeaderboardItem[]> {
  const queryMode = mode === "all" ? "all" : mode;
  const response = await fetch(`${API_BASE}/scores/leaderboard?season=2&limit=10&mode=${queryMode}`);
  if (!response.ok) throw new Error("Leaderboard unavailable");
  const rows = (await response.json()) as LeaderboardItem[];
  return rows.map((row) => ({ ...row, nickname: cleanNickname(row.nickname) }));
}

export async function submitScore(
  accessToken: string,
  payload: {
    score: number;
    lines: number;
    level: number;
    mode: GameMode;
    clientGameId: string;
  },
): Promise<void> {
  const body = {
    score: payload.score,
    lines: payload.lines,
    level: payload.level,
    mode: payload.mode,
    season: 2,
    platform: "telegram_web",
    client_game_id: payload.clientGameId,
  };

  const response = await fetch(`${API_BASE}/scores`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    if (response.status === 401) throw new Error("unauthorized");
    if (response.status === 503) {
      await new Promise((resolve) => window.setTimeout(resolve, 600));
      const retry = await fetch(`${API_BASE}/scores`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
      });
      if (retry.ok || retry.status === 409) return;
      if (retry.status === 401) throw new Error("unauthorized");
    }
    if (response.status === 409) return;
    throw new Error("Score was not saved");
  }
}
