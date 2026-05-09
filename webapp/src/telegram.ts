type TelegramUser = {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
};

type TelegramWebApp = {
  initData: string;
  initDataUnsafe?: { user?: TelegramUser; chat?: { id: number; type?: string } };
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
  viewportHeight?: number;
  viewportStableHeight?: number;
  ready: () => void;
  expand: () => void;
  onEvent?: (eventType: "viewportChanged", eventHandler: () => void) => void;
  offEvent?: (eventType: "viewportChanged", eventHandler: () => void) => void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export type TelegramContext = {
  isTelegram: boolean;
  isLocalDebug: boolean;
  initData: string;
  user: TelegramUser | null;
  theme: Record<string, string>;
  /** Telegram group/supergroup chat id when launched from a group context. */
  groupChatId: number | null;
};

/**
 * Detect group chat id from multiple sources:
 * 1. Telegram initDataUnsafe.chat (when Telegram provides it)
 * 2. URL query parameter `tg_chat_id` (set by bot URL button in groups)
 */
function detectGroupChatId(webApp: TelegramWebApp | undefined): number | null {
  // Source 1: Telegram initDataUnsafe chat object
  const chat = webApp?.initDataUnsafe?.chat;
  if (chat && typeof chat.id === "number" && (chat.type === "group" || chat.type === "supergroup")) {
    return chat.id;
  }

  // Source 2: URL query parameter (used when bot sends URL button in groups)
  const params = new URLSearchParams(window.location.search);
  const rawChatId = params.get("tg_chat_id");
  if (rawChatId) {
    const parsed = Number(rawChatId);
    if (Number.isFinite(parsed) && parsed !== 0) {
      return parsed;
    }
  }

  return null;
}

export function initTelegram(): TelegramContext {
  const webApp = window.Telegram?.WebApp;
  if (webApp) {
    try {
      webApp.ready();
      webApp.expand();
    } catch {
      // Telegram SDK calls are best-effort; the game should keep loading.
    }
  }

  const isLocalDebug = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  return {
    isTelegram: Boolean(webApp?.initData),
    isLocalDebug,
    initData: webApp?.initData ?? "",
    user: webApp?.initDataUnsafe?.user ?? null,
    theme: webApp?.themeParams ?? {},
    groupChatId: detectGroupChatId(webApp),
  };
}

export function applyTelegramTheme(theme: Record<string, string>): void {
  const root = document.documentElement;
  if (theme.bg_color) root.style.setProperty("--tg-bg", theme.bg_color);
  if (theme.text_color) root.style.setProperty("--tg-text", theme.text_color);
  if (theme.button_color) root.style.setProperty("--accent", theme.button_color);
  if (theme.hint_color) root.style.setProperty("--muted", theme.hint_color);
}

function applyTelegramViewport(webApp: TelegramWebApp | undefined): void {
  const height = webApp?.viewportHeight || window.visualViewport?.height || window.innerHeight;
  const stableHeight = webApp?.viewportStableHeight || height;
  document.documentElement.style.setProperty("--tg-viewport-height", `${Math.floor(height)}px`);
  document.documentElement.style.setProperty("--tg-stable-viewport-height", `${Math.floor(stableHeight)}px`);
}

export function bindTelegramViewport(): () => void {
  const webApp = window.Telegram?.WebApp;
  const update = () => applyTelegramViewport(webApp);
  update();
  webApp?.onEvent?.("viewportChanged", update);
  window.visualViewport?.addEventListener("resize", update);
  window.addEventListener("resize", update);
  return () => {
    webApp?.offEvent?.("viewportChanged", update);
    window.visualViewport?.removeEventListener("resize", update);
    window.removeEventListener("resize", update);
  };
}
