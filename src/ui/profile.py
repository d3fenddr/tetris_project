from __future__ import annotations

import queue
import threading
from typing import Callable

import pygame

from src.config import (
    BLACK,
    BUTTON_DEBOUNCE_MS,
    FPS,
    GRAY,
    MENU_BUTTON_FONT_SIZE,
    MENU_BUTTON_HEIGHT,
    MENU_BUTTON_WIDTH,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    RED,
    WHITE,
)
from src.services.account_service import AccountService
from src.services.backend_client import BackendClientError
from src.state import AppState
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
        draw_text(screen, title, 30, WHITE, screen.get_width() // 2, 90)
        draw_text(screen, label, 22, GRAY, screen.get_width() // 2, 165)
        display = "*" * len(value) if hidden else (value or "_")
        draw_text(screen, display, 28, RED, screen.get_width() // 2, 215)
        draw_text(screen, "ENTER to confirm | ESC to cancel", 18, GRAY, screen.get_width() // 2, screen.get_height() - 42)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
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
        draw_text(screen, title, 28, WHITE, screen.get_width() // 2, 140)
        draw_text(screen, message[:45], 18, GRAY, screen.get_width() // 2, 210)
        draw_text(screen, "Press any key", 18, WHITE, screen.get_width() // 2, 290)
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
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
    active_field = "nickname"
    message = "Enter your Season 2 account. New nicknames are created automatically."
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
        message = "Connecting to Season 2 backend..."

        def worker() -> None:
            try:
                account, created = account_service.authenticate_or_register(clean_nickname, password)
                result_queue.put((True, "Account created." if created else "Logged in.", account))
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
        draw_text_shadow(screen, "SEASON 2", 42, WHITE, screen.get_width() // 2, 78)
        draw_text(screen, "Account Required", 24, MUTED_TEXT, screen.get_width() // 2, 122)

        panel = pygame.Rect(26, 158, screen.get_width() - 52, 296)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)

        fields = [
            ("nickname", "Nickname", nickname, False, panel.y + 72),
            ("password", "Password", password, True, panel.y + 146),
        ]
        mouse_pos = pygame.mouse.get_pos()
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
        button_rect.center = (screen.get_width() // 2, panel.y + 226)
        draw_button(
            screen,
            button_rect,
            "Continue",
            MENU_BUTTON_FONT_SIZE,
            hovered=button_rect.collidepoint(mouse_pos),
            selected=True,
            enabled=not loading,
        )

        for idx, line in enumerate(_wrap_message(message)):
            draw_text(screen, line, 14, MUTED_TEXT, screen.get_width() // 2, panel.bottom + 32 + idx * 18)
        if loading:
            draw_text(screen, "Please wait...", 18, WHITE, screen.get_width() // 2, panel.bottom + 96)
        else:
            draw_text(screen, "ESC exits", 16, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 30)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
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
                    if button_rect.collidepoint(event.pos):
                        start_auth()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    raise SystemExit
                if event.key == pygame.K_TAB:
                    active_field = "password" if active_field == "nickname" else "nickname"
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
        draw_text(screen, title, 26, WHITE, screen.get_width() // 2, 120)
        draw_text(screen, message[:44], 17, GRAY, screen.get_width() // 2, 190)
        draw_text(screen, "Y / ENTER: yes", 20, WHITE, screen.get_width() // 2, 285)
        draw_text(screen, "ESC: no", 20, GRAY, screen.get_width() // 2, 325)
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
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
) -> None:
    last_click_ms = 0
    profile: dict | None = None
    if state.account and state.account.access_token:
        try:
            profile = account_service.refresh_current_user()
            if profile:
                state.account = account_service.load_account()
                if state.account:
                    state.player_name = state.account.username
                    persist_state()
        except BackendClientError:
            profile = None

    while True:
        screen.fill(BLACK)
        logged_in = state.account is not None and bool(state.account.access_token)
        draw_text_shadow(screen, "Profile", 36, WHITE, screen.get_width() // 2, 55)
        buttons: list[tuple[pygame.Rect, str]] = []

        if logged_in:
            nickname = state.account.username if state.account else ""
            draw_text(screen, f"Nickname: {nickname}", 24, WHITE, screen.get_width() // 2, 125)
            if profile:
                draw_text(screen, f"Best: {profile.get('best_score', 0)}", 20, GRAY, screen.get_width() // 2, 165)
                draw_text(screen, f"Games: {profile.get('games_played', 0)}", 20, GRAY, screen.get_width() // 2, 195)
            options = [("Change Nickname", "change"), ("Logout", "logout")]
        else:
            draw_text(screen, "Account session is missing.", 22, RED, screen.get_width() // 2, 130)
            draw_text(screen, "Restart and sign in to continue.", 17, GRAY, screen.get_width() // 2, 160)
            options = []

        mx, my = pygame.mouse.get_pos()
        for idx, (label, action) in enumerate(options):
            y = 280 + idx * 58
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
                        account_service.logout()
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
