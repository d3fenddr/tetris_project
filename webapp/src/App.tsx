import { useCallback, useEffect, useRef, useState } from "react";
import {
  authenticateTelegram,
  ApiError,
  AuthSession,
  fetchLeaderboard,
  GameMode,
  LeaderboardItem,
  loginWithPassword,
  submitScore,
} from "./api";
import { AccountScreen } from "./components/AccountScreen";
import { GameCanvas } from "./components/GameCanvas";
import { Leaderboard } from "./components/Leaderboard";
import { MainMenu } from "./components/MainMenu";
import { ModeSelect } from "./components/ModeSelect";
import { useGameControls } from "./controls";
import { GameAction, GameSnapshot, TetrisGame } from "./game/tetris";
import { applyTelegramTheme, bindTelegramViewport, initTelegram, TelegramContext } from "./telegram";

type Screen = "menu" | "account" | "mode" | "game" | "leaderboard";
type LeaderboardMode = GameMode | "all";

const SESSION_KEY = "tetris.webapp.session";
const AUTH_MODE_KEY = "tetris.webapp.authMode";
const SOUND_KEY = "tetris.webapp.sound";
const MODE_KEY = "tetris.webapp.mode";
const MENU_MUSIC = "/assets/audio/music/menu-music.mp3";
const GAME_MUSIC = "/assets/audio/music/game-music.mp3";

function readSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function persistSession(session: AuthSession | null, mode?: "telegram" | "database"): void {
  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    if (mode) localStorage.setItem(AUTH_MODE_KEY, mode);
  } else {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(AUTH_MODE_KEY);
  }
}

function createDebugSession(): AuthSession {
  return {
    accessToken: "",
    refreshToken: "",
    user: { id: 0, nickname: "Local player", games_played: 0, best_score: 0 },
  };
}

export function App() {
  const gameRef = useRef(new TetrisGame());
  const boardRef = useRef<HTMLDivElement | null>(null);
  const submittedGameId = useRef<string | null>(null);
  const menuAudioRef = useRef<HTMLAudioElement | null>(null);
  const gameAudioRef = useRef<HTMLAudioElement | null>(null);
  const [telegram, setTelegram] = useState<TelegramContext | null>(null);
  const [screen, setScreen] = useState<Screen>("menu");
  const [session, setSession] = useState<AuthSession | null>(() => readSession());
  const [authStatus, setAuthStatus] = useState("Choose Telegram or existing account.");
  const [mode, setMode] = useState<GameMode>(() => (localStorage.getItem(MODE_KEY) as GameMode) || "normal");
  const [soundEnabled, setSoundEnabled] = useState(() => localStorage.getItem(SOUND_KEY) !== "off");
  const [snapshot, setSnapshot] = useState<GameSnapshot>(() => gameRef.current.snapshot());
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([]);
  const [leaderboardMode, setLeaderboardMode] = useState<LeaderboardMode>("all");
  const [leaderboardLoading, setLeaderboardLoading] = useState(false);
  const [leaderboardError, setLeaderboardError] = useState("");
  const [saveStatus, setSaveStatus] = useState("");

  const refreshLeaderboard = useCallback(async (selectedMode: LeaderboardMode) => {
    setLeaderboardLoading(true);
    setLeaderboardError("");
    try {
      setLeaderboard(await fetchLeaderboard(selectedMode));
    } catch (error) {
      setLeaderboardError(error instanceof Error ? error.message : "Leaderboard is unavailable.");
    } finally {
      setLeaderboardLoading(false);
    }
  }, []);

  const openLeaderboard = useCallback((selectedMode: LeaderboardMode = "all") => {
    setLeaderboardMode(selectedMode);
    refreshLeaderboard(selectedMode);
    setScreen("leaderboard");
  }, [refreshLeaderboard]);

  useEffect(() => {
    const context = initTelegram();
    applyTelegramTheme(context.theme);
    const unbindViewport = bindTelegramViewport();
    setTelegram(context);
    if (context.isTelegram) {
      setAuthStatus("Telegram is ready.");
    } else if (context.isLocalDebug) {
      setAuthStatus("Local debug mode. Login is optional; scores need a real token.");
      if (!readSession()) setSession(createDebugSession());
    } else {
      setAuthStatus("Open from Telegram or login with an existing account.");
    }
    refreshLeaderboard("all");
    return unbindViewport;
  }, [refreshLeaderboard]);

  useEffect(() => {
    menuAudioRef.current = new Audio(MENU_MUSIC);
    gameAudioRef.current = new Audio(GAME_MUSIC);
    for (const audio of [menuAudioRef.current, gameAudioRef.current]) {
      audio.loop = true;
      audio.volume = 0.07;
    }
    return () => {
      menuAudioRef.current?.pause();
      gameAudioRef.current?.pause();
    };
  }, []);

  const playAudio = useCallback((track: "menu" | "game", restart = false) => {
    const menu = menuAudioRef.current;
    const game = gameAudioRef.current;
    if (!menu || !game) return;
    const active = track === "menu" ? menu : game;
    const inactive = track === "menu" ? game : menu;
    if (restart) active.currentTime = 0;
    if (!soundEnabled) {
      menu.pause();
      game.pause();
      return;
    }
    inactive.pause();
    void active.play().catch(() => undefined);
  }, [soundEnabled]);

  useEffect(() => {
    localStorage.setItem(SOUND_KEY, soundEnabled ? "on" : "off");
    if (!soundEnabled) {
      menuAudioRef.current?.pause();
      gameAudioRef.current?.pause();
    } else if (screen === "game" && snapshot.status === "playing") {
      playAudio("game");
    } else if (screen === "game") {
      gameAudioRef.current?.pause();
    } else {
      playAudio("menu");
    }
  }, [soundEnabled, screen, snapshot.status, playAudio]);

  const runAction = useCallback((action: GameAction) => {
    const changed = gameRef.current.action(action);
    if (changed) setSnapshot(gameRef.current.snapshot());
  }, []);

  const { startHold, stopHold, stopAllHolds } = useGameControls({
    enabled: screen === "game" && snapshot.status === "playing",
    onAction: runAction,
  });

  const continueWithTelegram = useCallback(async () => {
    if (!telegram?.initData) {
      setAuthStatus("Telegram initData is unavailable in this browser.");
      return;
    }
    setAuthStatus("Signing in with Telegram...");
    try {
      const authSession = await authenticateTelegram(telegram.initData);
      persistSession(authSession, "telegram");
      setSession(authSession);
      setAuthStatus(`Signed in as ${authSession.user.nickname}`);
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "Telegram sign-in failed. Please try again.");
    }
  }, [telegram]);

  const loginExisting = useCallback(async (nickname: string, password: string) => {
    const authSession = await loginWithPassword(nickname, password);
    persistSession(authSession, "database");
    setSession(authSession);
    setAuthStatus(`Signed in as ${authSession.user.nickname}`);
  }, []);

  const logout = useCallback(() => {
    persistSession(null);
    setSession(null);
    setAuthStatus("Choose Telegram or existing account.");
  }, []);

  const startGame = useCallback((selectedMode: GameMode = mode) => {
    localStorage.setItem(MODE_KEY, selectedMode);
    setMode(selectedMode);
    submittedGameId.current = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    setSaveStatus("");
    gameRef.current.start(selectedMode);
    setSnapshot(gameRef.current.snapshot());
    setScreen("game");
    playAudio("game", true);
  }, [mode, playAudio]);

  useEffect(() => {
    let animationId = 0;
    let lastTime = performance.now();
    const frame = (time: number) => {
      const delta = time - lastTime;
      lastTime = time;
      if (gameRef.current.tick(delta)) setSnapshot(gameRef.current.snapshot());
      animationId = requestAnimationFrame(frame);
    };
    animationId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(animationId);
  }, []);

  useEffect(() => {
    if (snapshot.status !== "game_over" || !submittedGameId.current) return;
    gameAudioRef.current?.pause();
    if (!session?.accessToken) {
      setSaveStatus(telegram?.isLocalDebug ? "Debug game finished. Score not submitted." : "Score was not saved. Please log in again.");
      return;
    }
    const gameId = submittedGameId.current;
    submittedGameId.current = null;
    setSaveStatus("Saving score...");
    submitScore(session.accessToken, {
      score: snapshot.score,
      lines: snapshot.lines,
      level: snapshot.level,
      mode: snapshot.mode,
      clientGameId: gameId,
    })
      .then(() => {
        setSaveStatus("Score saved.");
        refreshLeaderboard(snapshot.mode);
      })
      .catch((error: any) => {
        setSaveStatus(
          error instanceof ApiError && error.status === 401
            ? "Score was not saved. Please log in again."
            : error instanceof Error
              ? error.message
              : "Score was not saved. Please try again later.",
        );
      });
  }, [snapshot, session, telegram, refreshLeaderboard]);

  const openMenu = () => {
    stopAllHolds();
    const returningFromGame = screen === "game";
    setScreen("menu");
    playAudio("menu", returningFromGame);
  };

  return (
    <main className="app-shell">
      {screen === "menu" && (
        <MainMenu
          session={session}
          authStatus={authStatus}
          soundEnabled={soundEnabled}
          onPlay={() => setScreen(session ? "mode" : "account")}
          onLeaderboard={() => {
            openLeaderboard("all");
          }}
          onAccount={() => setScreen("account")}
          onToggleSound={() => setSoundEnabled((value) => !value)}
        />
      )}

      {screen === "account" && (
        <AccountScreen
          session={session}
          telegramAvailable={Boolean(telegram?.isTelegram)}
          authStatus={authStatus}
          onTelegram={continueWithTelegram}
          onLogin={loginExisting}
          onLogout={logout}
          onBack={() => setScreen("menu")}
        />
      )}

      {screen === "mode" && <ModeSelect selected={mode} onSelect={startGame} onBack={openMenu} />}

      {screen === "game" && (
        <GameCanvas
          snapshot={snapshot}
          boardRef={boardRef}
          bestText={
            session?.user.best_score
              ? `${session.user.nickname} - ${session.user.best_score}`
              : "Karim - 2200"
          }
          saveStatus={saveStatus}
          soundEnabled={soundEnabled}
          startHold={startHold}
          stopHold={stopHold}
          tap={runAction}
          onToggleSound={() => setSoundEnabled((value) => !value)}
          onRestart={() => startGame(snapshot.mode)}
          onChangeMode={() => setScreen("mode")}
          onMainMenu={openMenu}
          onLeaderboard={() => {
            openLeaderboard(snapshot.mode);
          }}
        />
      )}

      {screen === "leaderboard" && (
        <Leaderboard
          rows={leaderboard}
          loading={leaderboardLoading}
          error={leaderboardError}
          activeMode={leaderboardMode}
          currentUserId={session?.user.id}
          onModeChange={(selectedMode) => {
            setLeaderboardMode(selectedMode);
            refreshLeaderboard(selectedMode);
          }}
          onBack={openMenu}
        />
      )}
    </main>
  );
}
