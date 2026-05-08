type TelegramUser = {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
};

type TelegramWebApp = {
  initData: string;
  initDataUnsafe?: { user?: TelegramUser };
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
  ready: () => void;
  expand: () => void;
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
};

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
  };
}

export function applyTelegramTheme(theme: Record<string, string>): void {
  const root = document.documentElement;
  if (theme.bg_color) root.style.setProperty("--tg-bg", theme.bg_color);
  if (theme.text_color) root.style.setProperty("--tg-text", theme.text_color);
  if (theme.button_color) root.style.setProperty("--accent", theme.button_color);
  if (theme.hint_color) root.style.setProperty("--muted", theme.hint_color);
}
