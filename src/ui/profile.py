from __future__ import annotations

import queue
import threading
from datetime import datetime
from typing import Callable

import pygame

from src.config import (
    BLACK,
    BUTTON_DEBOUNCE_MS,
    FORM_MAX_WIDTH,
    FPS,
    GRAY,
    MENU_BUTTON_FONT_SIZE,
    MENU_BUTTON_HEIGHT,
    MENU_BUTTON_WIDTH,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    PROFILE_PANEL_MAX_WIDTH,
    RED,
    WHITE,
)
from src.services.account_service import AccountService
from src.services.backend_client import BackendClientError
from src.state import AppState
from src.utils.layout import content_rect, handle_resize_event
from src.utils.ui_helpers import draw_button, draw_panel, draw_text, draw_text_shadow


def _wrap_message(message: str, width: int = 38) -> list[str]:
    words = message.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:3]


def _format_profile_date(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Unknown"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return raw[:10] if len(raw) >= 10 else raw


def _draw_loading_frame(
    screen: pygame.Surface,
    title: str,
    message: str,
    started_ms: int,
) -> None:
    screen.fill(BLACK)
    draw_text_shadow(screen, title, 34, WHITE, screen.get_width() // 2, 122)
    panel = content_rect(screen, FORM_MAX_WIDTH, 190, y=195)
    draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
    dots = "." * ((pygame.time.get_ticks() - started_ms) // 320 % 4)
    draw_text(screen, f"{message}{dots}", 22, WHITE, panel.centerx, panel.centery - 8)
    draw_text(screen, "Please wait", 16, MUTED_TEXT, panel.centerx, panel.centery + 28)


def _wait_with_loading(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    title: str,
    message: str,
    worker: Callable[[], object],
) -> tuple[bool, object | None, str]:
    result_queue: "queue.Queue[tuple[bool, object | None, str]]" = queue.Queue()

    def run_worker() -> None:
        try:
            result_queue.put((True, worker(), ""))
        except Exception as exc:
            result_queue.put((False, None, str(exc)))

    threading.Thread(target=run_worker, daemon=True).start()
    started_ms = pygame.time.get_ticks()
    while True:
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            pass

        _draw_loading_frame(screen, title, message, started_ms)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)


def _prompt_text(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    title: str,
    label: str,
    hidden: bool = False,
) -> str | None:
    value = ""
    while True:
        screen.fill(BLACK)
        panel = content_rect(screen, FORM_MAX_WIDTH, 260, y=92)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        draw_text(screen, title, 30, WHITE, panel.centerx, panel.y + 42)
        draw_text(screen, label, 22, GRAY, panel.centerx, panel.y + 112)
        display = "*" * len(value) if hidden else (value or "_")
        draw_text(screen, display, 28, RED, panel.centerx, panel.y + 162)
        draw_text(screen, "ENTER to confirm | ESC to cancel", 18, GRAY, screen.get_width() // 2, screen.get_height() - 42)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return value.strip()
                if event.key == pygame.K_BACKSPACE:
                    value = value[:-1]
                    continue
                if event.unicode and event.unicode.isprintable() and len(value) < 128:
                    value += event.unicode


def _message_screen(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    title: str,
    message: str,
) -> None:
    while True:
        screen.fill(BLACK)
        panel = content_rect(screen, FORM_MAX_WIDTH, 220, y=120)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        draw_text(screen, title, 28, WHITE, panel.centerx, panel.y + 42)
        draw_text(screen, message[:45], 18, GRAY, panel.centerx, panel.y + 100)
        draw_text(screen, "Press any key", 18, WHITE, panel.centerx, panel.y + 168)
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return


def account_startup_screen(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    account_service: AccountService,
    persist_state: Callable[[], None],
) -> None:
    nickname = state.account.username if state.account else state.player_name
    password = ""
    mode = "login"
    active_field = "nickname"
    message = "Use your existing Season 2 account."
    loading = False
    result_queue: "queue.Queue[tuple[bool, str, object]]" = queue.Queue()
    last_click_ms = 0

    def start_auth() -> None:
        nonlocal loading, message
        clean_nickname = nickname.strip()
        if not clean_nickname or not password:
            message = "Nickname and password are required."
            return
        loading = True
        message = "Logging in..." if mode == "login" else "Creating account..."

        def worker() -> None:
            try:
                if mode == "register":
                    account = account_service.register(clean_nickname, password)
                else:
                    account = account_service.login(clean_nickname, password)
                result_queue.put((True, "Account created." if mode == "register" else "Logged in.", account))
            except BackendClientError as exc:
                result_queue.put((False, str(exc), None))

        threading.Thread(target=worker, daemon=True).start()

    while True:
        if loading:
            try:
                success, result_message, payload = result_queue.get_nowait()
                loading = False
                if success:
                    state.account = payload  # type: ignore[assignment]
                    if state.account:
                        state.player_name = state.account.username
                    persist_state()
                    return
                message = result_message or "Backend is unavailable. Online account and leaderboard require connection."
            except queue.Empty:
                pass

        screen.fill(BLACK)
        draw_text_shadow(screen, "SEASON 2 ACCOUNT", 36, WHITE, screen.get_width() // 2, 76)

        panel = content_rect(screen, FORM_MAX_WIDTH, 380, y=132)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        tab_width = (panel.width - 68) // 2
        login_tab = pygame.Rect(panel.x + 28, panel.y + 28, tab_width, 42)
        register_tab = pygame.Rect(login_tab.right + 12, panel.y + 28, tab_width, 42)
        mouse_pos = pygame.mouse.get_pos()
        draw_button(screen, login_tab, "Login", 20, hovered=login_tab.collidepoint(mouse_pos), selected=mode == "login")
        draw_button(
            screen,
            register_tab,
            "Register",
            20,
            hovered=register_tab.collidepoint(mouse_pos),
            selected=mode == "register",
        )
        hint = "Use your existing Season 2 account." if mode == "login" else "Create a new Season 2 account."
        draw_text(screen, hint, 15, MUTED_TEXT, panel.centerx, panel.y + 94)

        fields = [
            ("nickname", "Nickname", nickname, False, panel.y + 155),
            ("password", "Password", password, True, panel.y + 229),
        ]
        field_rects: list[tuple[str, pygame.Rect]] = []
        for field_name, label, value, hidden, y in fields:
            draw_text(screen, label, 16, MUTED_TEXT, panel.centerx, y - 31)
            rect = pygame.Rect(panel.x + 28, y - 18, panel.width - 56, 42)
            selected = active_field == field_name
            pygame.draw.rect(screen, (18, 20, 28), rect, border_radius=7)
            pygame.draw.rect(screen, RED if selected else PANEL_BORDER, rect, width=1, border_radius=7)
            display = "*" * len(value) if hidden else value
            draw_text(screen, display or "_", 22, WHITE, rect.centerx, rect.centery)
            field_rects.append((field_name, rect))

        button_rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
        button_rect.width = min(MENU_BUTTON_WIDTH, panel.width - 70)
        button_rect.center = (screen.get_width() // 2, panel.y + 306)
        draw_button(
            screen,
            button_rect,
            "Login" if mode == "login" else "Create Account",
            MENU_BUTTON_FONT_SIZE,
            hovered=button_rect.collidepoint(mouse_pos),
            selected=True,
            enabled=not loading,
        )

        for idx, line in enumerate(_wrap_message(message)):
            color = RED if "wrong" in message.lower() or "not found" in message.lower() or "unavailable" in message.lower() or "already" in message.lower() else MUTED_TEXT
            draw_text(screen, line, 14, color, screen.get_width() // 2, panel.bottom + 28 + idx * 18)
        if loading:
            draw_text(screen, "Please wait...", 18, WHITE, screen.get_width() // 2, panel.bottom + 96)
        else:
            draw_text(screen, "ESC exits", 16, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 30)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if loading:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                for field_name, rect in field_rects:
                    if rect.collidepoint(event.pos):
                        active_field = field_name
                        break
                else:
                    if login_tab.collidepoint(event.pos):
                        mode = "login"
                        message = "Use your existing Season 2 account."
                    elif register_tab.collidepoint(event.pos):
                        mode = "register"
                        message = "Create a new Season 2 account."
                    elif button_rect.collidepoint(event.pos):
                        start_auth()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    raise SystemExit
                if event.key == pygame.K_TAB:
                    active_field = "password" if active_field == "nickname" else "nickname"
                    continue
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    mode = "register" if mode == "login" else "login"
                    message = "Use your existing Season 2 account." if mode == "login" else "Create a new Season 2 account."
                    continue
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_auth()
                    continue
                if event.key == pygame.K_BACKSPACE:
                    if active_field == "nickname":
                        nickname = nickname[:-1]
                    else:
                        password = password[:-1]
                    continue
                if event.unicode and event.unicode.isprintable():
                    if active_field == "nickname" and len(nickname) < 20:
                        nickname += event.unicode
                    elif active_field == "password" and len(password) < 128:
                        password += event.unicode


def _confirm(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    title: str,
    message: str,
) -> bool:
    while True:
        screen.fill(BLACK)
        panel = content_rect(screen, FORM_MAX_WIDTH, 250, y=105)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        draw_text(screen, title, 26, WHITE, panel.centerx, panel.y + 42)
        draw_text(screen, message[:44], 17, GRAY, panel.centerx, panel.y + 105)
        draw_text(screen, "Y / ENTER: yes", 20, WHITE, panel.centerx, panel.y + 178)
        draw_text(screen, "ESC: no", 20, GRAY, panel.centerx, panel.y + 218)
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False


def _login_or_register(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    account_service: AccountService,
    state: AppState,
    persist_state: Callable[[], None],
    register: bool,
) -> None:
    nickname = _prompt_text(screen, clock, "Register" if register else "Login", "Nickname")
    if not nickname:
        return
    password = _prompt_text(screen, clock, "Register" if register else "Login", "Password", hidden=True)
    if not password:
        return

    try:
        if register:
            account_service.register(nickname, password)
        account = account_service.login(nickname, password)
        state.account = account
        state.player_name = account.username
        persist_state()
        _message_screen(screen, clock, "Account ready", f"Logged in as {account.username}.")
    except BackendClientError as exc:
        _message_screen(screen, clock, "Account error", str(exc))


def profile_screen(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    account_service: AccountService,
    persist_state: Callable[[], None],
    on_logout: Callable[[], None] | None = None,
) -> None:
    last_click_ms = 0
    profile: dict | None = None
    profile_error = ""
    if state.account and state.account.access_token:
        success, loaded_profile, error = _wait_with_loading(
            screen,
            clock,
            "Profile",
            "Loading account",
            account_service.refresh_current_user,
        )
        if success and isinstance(loaded_profile, dict):
            profile = loaded_profile
            state.account = account_service.load_account()
            if state.account:
                state.player_name = state.account.username
                persist_state()
        else:
            profile_error = error or "Could not refresh profile."

    while True:
        screen.fill(BLACK)
        logged_in = state.account is not None and bool(state.account.access_token)
        draw_text_shadow(screen, "Profile", 36, WHITE, screen.get_width() // 2, 55)
        buttons: list[tuple[pygame.Rect, str]] = []

        if logged_in:
            nickname = state.account.username if state.account else ""
            summary = content_rect(screen, PROFILE_PANEL_MAX_WIDTH, 240, y=92)
            draw_panel(screen, summary, PANEL_BG, PANEL_BORDER)
            draw_text(screen, nickname, 26, WHITE, summary.centerx, summary.y + 34)
            draw_text(screen, "Season 2 Account", 15, MUTED_TEXT, summary.centerx, summary.y + 62)
            if profile:
                rows = [
                    ("User ID", str(profile.get("id", state.account.user_id or "-"))),
                    ("Best Score", str(profile.get("best_score", 0))),
                    ("Games Played", str(profile.get("games_played", 0))),
                    ("Season Rank", str(profile.get("current_season_rank") or "Unranked")),
                    ("Joined", _format_profile_date(profile.get("created_at"))),
                    ("Last Login", _format_profile_date(profile.get("last_login_at"))),
                ]
            else:
                rows = [
                    ("User ID", str(state.account.user_id or "-")),
                    ("Status", "Offline profile cache"),
                    ("Best Score", "Unavailable"),
                    ("Games Played", "Unavailable"),
                    ("Season Rank", "Unavailable"),
                ]
            for idx, (label, value) in enumerate(rows):
                y = summary.y + 96 + idx * 22
                draw_text(screen, label, 14, MUTED_TEXT, summary.x + 72, y)
                draw_text(screen, value, 14, WHITE, summary.right - 82, y)
            if profile_error:
                draw_text(screen, profile_error[:38], 13, RED, summary.centerx, summary.bottom - 14)
            options = [("Change Nickname", "change"), ("Logout", "logout")]
        else:
            draw_text(screen, "Account session is missing.", 22, RED, screen.get_width() // 2, 130)
            draw_text(screen, "Restart and sign in to continue.", 17, GRAY, screen.get_width() // 2, 160)
            options = []

        mx, my = pygame.mouse.get_pos()
        for idx, (label, action) in enumerate(options):
            y = 405 + idx * 58
            rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
            rect.center = (screen.get_width() // 2, y)
            draw_button(screen, rect, label, 22, hovered=rect.collidepoint(mx, my), selected=idx == 0)
            buttons.append((rect, action))

        draw_text(screen, "ESC to return", 18, GRAY, screen.get_width() // 2, screen.get_height() - 26)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                for rect, action in buttons:
                    if not rect.collidepoint(event.pos):
                        continue
                    if action == "login":
                        _login_or_register(screen, clock, account_service, state, persist_state, register=False)
                    elif action == "register":
                        _login_or_register(screen, clock, account_service, state, persist_state, register=True)
                    elif action == "logout":
                        _wait_with_loading(
                            screen,
                            clock,
                            "Profile",
                            "Signing out",
                            account_service.logout,
                        )
                        if on_logout is not None:
                            on_logout()
                        state.account = None
                        persist_state()
                    elif action == "change":
                        if not _confirm(
                            screen,
                            clock,
                            "Change nickname?",
                            "Future results will use the new nickname.",
                        ):
                            continue
                        nickname = _prompt_text(screen, clock, "Change Nickname", "New nickname")
                        if not nickname:
                            continue
                        try:
                            account = account_service.change_nickname(nickname)
                            state.account = account
                            state.player_name = account.username
                            persist_state()
                            _message_screen(screen, clock, "Nickname changed", f"Now playing as {account.username}.")
                        except BackendClientError as exc:
                            _message_screen(screen, clock, "Nickname error", str(exc))
                    return
