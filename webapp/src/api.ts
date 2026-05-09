const API_BASE = (import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const IS_DEV = import.meta.env.DEV;

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
  user_id: number;
  nickname: string;
  score: number;
  lines: number;
  level: number;
  mode: string;
  season: number;
  created_at: string;
};

export type GameMode = "peaceful" | "easy" | "normal" | "hard";

export class ApiError extends Error {
  status?: number;
  detail?: string;

  constructor(message: string, status?: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function responseDetail(response: Response): Promise<string> {
  const text = await response.text().catch(() => "");
  if (!text) return "";
  try {
    const payload = JSON.parse(text);
    return String(payload.detail || payload.message || text);
  } catch {
    return text;
  }
}

function networkMessage(endpoint: string): string {
  return `Cannot reach backend at ${API_BASE}${endpoint}. Check VITE_BACKEND_URL, Render availability, HTTPS, and CORS.`;
}

async function requestJson<T>(
  endpoint: string,
  init: RequestInit = {},
  friendlyName = "Request",
): Promise<T> {
  const url = apiUrl(endpoint);
  if (IS_DEV) console.info(`[api] ${init.method || "GET"} ${url}`);

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (error) {
    const message = networkMessage(endpoint);
    if (IS_DEV) console.error(`[api] ${message}`, error);
    throw new ApiError(message);
  }

  if (!response.ok) {
    const detail = await responseDetail(response);
    const message =
      response.status === 401
        ? `${friendlyName} failed: unauthorized. Please log in again.`
        : `${friendlyName} failed: backend returned ${response.status}${detail ? ` - ${detail}` : ""}`;
    if (IS_DEV) console.error(`[api] ${message}`);
    throw new ApiError(message, response.status, detail);
  }

  return response.json() as Promise<T>;
}

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
  const payload = await requestJson<any>(
    "/telegram/auth",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: initData }),
    },
    "Telegram sign-in",
  );
  return mapSession(payload);
}

export async function loginWithPassword(nickname: string, password: string): Promise<AuthSession> {
  const payload = await requestJson<any>(
    "/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname, password }),
    },
    "Login",
  );
  return mapSession(payload);
}

export async function fetchLeaderboard(mode: GameMode | "all" = "normal"): Promise<LeaderboardItem[]> {
  const queryMode = mode === "all" ? "all" : mode;
  const rows = await requestJson<LeaderboardItem[]>(
    `/scores/leaderboard?season=2&limit=10&mode=${encodeURIComponent(queryMode)}`,
    {},
    "Leaderboard",
  );
  return rows.map((row) => ({ ...row, nickname: cleanNickname(row.nickname) }));
}

export async function fetchGroupLeaderboard(
  chatId: number,
  mode: GameMode | "all" = "all",
): Promise<LeaderboardItem[]> {
  const queryMode = mode === "all" ? "all" : mode;
  const rows = await requestJson<LeaderboardItem[]>(
    `/scores/telegram/group/${chatId}?limit=20&mode=${encodeURIComponent(queryMode)}`,
    {},
    "Group leaderboard",
  );
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
    telegramChatId?: number | null;
  },
): Promise<void> {
  const body: Record<string, unknown> = {
    score: payload.score,
    lines: payload.lines,
    level: payload.level,
    mode: payload.mode,
    season: 2,
    platform: "telegram_web",
    client_game_id: payload.clientGameId,
  };
  if (payload.telegramChatId != null) {
    body.telegram_chat_id = payload.telegramChatId;
  }

  const init: RequestInit = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  };

  try {
    await requestJson<unknown>("/scores", init, "Score save");
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) return;
    if (error instanceof ApiError && error.status === 503) {
      await new Promise((resolve) => window.setTimeout(resolve, 600));
      try {
        await requestJson<unknown>("/scores", init, "Score save retry");
        return;
      } catch (retryError) {
        if (retryError instanceof ApiError && retryError.status === 409) return;
        throw retryError;
      }
    }
    throw error;
  }
}
