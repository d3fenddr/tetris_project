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
    KEY_REPEAT_INITIAL_DELAY_MS,
    KEY_REPEAT_MOVE_INTERVAL_MS,
    MENU_BUTTON_FONT_SIZE,
    MENU_BUTTON_HEIGHT,
    MENU_BUTTON_WIDTH,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    PROFILE_PANEL_MAX_WIDTH,
    RED,
    UI_SCALE_MAX,
    UI_SCALE_MIN,
    WHITE,
)
from src.services.account_service import AccountService
from src.services.backend_client import BackendClientError
from src.services.rewards import season_1_reward_for
from src.state import AppState
from src.ui.reward_badges import draw_medal_badge
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


def normalize_auth_error(error: object) -> str:
    raw = str(error or "").strip()
    lowered = raw.lower()
    if "password" in lowered and ("string_too_short" in lowered or "at least 6" in lowered or "min_length" in lowered):
        return "Password must be at least 6 characters."
    if "nickname" in lowered and ("string_too_short" in lowered or "at least 3" in lowered):
        return "Nickname must be at least 3 characters."
    if "already" in lowered or "taken" in lowered:
        return "This nickname is already taken."
    if "wrong" in lowered or "incorrect" in lowered or "invalid" in lowered:
        return "Nickname or password is incorrect."
    if "not found" in lowered:
        return "Account was not found."
    if "unavailable" in lowered or "timed out" in lowered:
        return "Account service is temporarily unavailable."
    if "[score-flow]" in raw or raw.startswith("[") or "{'" in raw or '"detail"' in raw:
        return "Something went wrong. Please try again."
    return raw or "Something went wrong. Please try again."


def _enable_text_key_repeat() -> None:
    pygame.key.set_repeat(KEY_REPEAT_INITIAL_DELAY_MS, KEY_REPEAT_MOVE_INTERVAL_MS)


def _disable_text_key_repeat() -> None:
    pygame.key.set_repeat(0)


def _auth_scale(screen: pygame.Surface) -> float:
    return max(UI_SCALE_MIN, min(UI_SCALE_MAX, screen.get_height() / 750))


def _scaled(value: int, scale: float, minimum: int) -> int:
    return max(minimum, int(value * scale))


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
    _enable_text_key_repeat()
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
                    _disable_text_key_repeat()
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    _disable_text_key_repeat()
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
    nickname = state.account.username if state.account else ""
    password = ""
    mode = "login"
    active_field = "nickname"
    message = "Use your existing Season 2 account."
    loading = False
    result_queue: "queue.Queue[tuple[bool, str, object]]" = queue.Queue()
    last_click_ms = 0
    _enable_text_key_repeat()

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
                print(f"[auth-flow] Auth failed: {exc}")
                result_queue.put((False, normalize_auth_error(exc), None))

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
                    _disable_text_key_repeat()
                    return
                message = normalize_auth_error(result_message)
            except queue.Empty:
                pass

        height = screen.get_height()
        scale = _auth_scale(screen)
        top_margin = _scaled(18, scale, 12)
        bottom_margin = _scaled(18, scale, 12)
        title_font = _scaled(36, scale, 26)
        tab_font = _scaled(20, scale, 15)
        hint_font = _scaled(15, scale, 12)
        label_font = _scaled(16, scale, 12)
        input_font = _scaled(22, scale, 16)
        button_font = _scaled(MENU_BUTTON_FONT_SIZE, scale, 17)
        message_font = _scaled(14, scale, 11)
        footer_font = _scaled(14, scale, 10)
        tab_height = _scaled(42, scale, 30)
        input_height = _scaled(42, scale, 32)
        button_height = _scaled(MENU_BUTTON_HEIGHT, scale, 32)
        panel_padding_x = _scaled(28, scale, 18)
        panel_padding_top = _scaled(28, scale, 18)
        gap_after_tabs = _scaled(24, scale, 14)
        field_gap = _scaled(32, scale, 20)
        gap_before_button = _scaled(24, scale, 16)
        title_block = _scaled(74, scale, 48)
        message_area = _scaled(64, scale, 44)
        footer_area = _scaled(24, scale, 18)
        panel_height = (
            panel_padding_top
            + tab_height
            + gap_after_tabs
            + _scaled(20, scale, 14)
            + field_gap
            + input_height * 2
            + gap_before_button
            + button_height
            + _scaled(22, scale, 12)
        )
        available_height = max(1, height - top_margin - bottom_margin)
        total_height = title_block + panel_height + message_area + footer_area
        if total_height > available_height:
            overflow = total_height - available_height
            panel_height = max(_scaled(300, scale, 276), panel_height - overflow)
            total_height = title_block + panel_height + message_area + footer_area
        start_y = max(top_margin, (height - total_height) // 2)
        title_y = start_y + _scaled(28, scale, 22)
        panel_y = start_y + title_block

        screen.fill(BLACK)
        draw_text_shadow(screen, "Season 2", title_font, WHITE, screen.get_width() // 2, title_y)

        panel = content_rect(screen, FORM_MAX_WIDTH, panel_height, y=panel_y, min_margin=18)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        tab_width = (panel.width - panel_padding_x * 2 - _scaled(12, scale, 8)) // 2
        login_tab = pygame.Rect(panel.x + panel_padding_x, panel.y + panel_padding_top, tab_width, tab_height)
        register_tab = pygame.Rect(login_tab.right + _scaled(12, scale, 8), panel.y + panel_padding_top, tab_width, tab_height)
        mouse_pos = pygame.mouse.get_pos()
        draw_button(screen, login_tab, "Login", tab_font, hovered=login_tab.collidepoint(mouse_pos), selected=mode == "login")
        draw_button(
            screen,
            register_tab,
            "Register",
            tab_font,
            hovered=register_tab.collidepoint(mouse_pos),
            selected=mode == "register",
        )
        hint_y = login_tab.bottom + _scaled(20, scale, 12)
        first_field_y = hint_y + _scaled(46, scale, 34)
        second_field_y = first_field_y + input_height + field_gap
        fields = [
            ("nickname", "Nickname", nickname, False, first_field_y),
            ("password", "Password", password, True, second_field_y),
        ]
        field_rects: list[tuple[str, pygame.Rect]] = []

        label_gap_above_input = _scaled(36, scale, 28)

        for field_name, label, value, hidden, y in fields:
            draw_text(screen, label, label_font, MUTED_TEXT, panel.centerx, y - label_gap_above_input)
            rect = pygame.Rect(panel.x + panel_padding_x, y - input_height // 2, panel.width - panel_padding_x * 2, input_height)
            selected = active_field == field_name
            pygame.draw.rect(screen, (18, 20, 28), rect, border_radius=7)
            pygame.draw.rect(screen, RED if selected else PANEL_BORDER, rect, width=1, border_radius=7)
            display = "*" * len(value) if hidden else value
            draw_text(screen, display or "_", input_font, WHITE, rect.centerx, rect.centery)
            field_rects.append((field_name, rect))

        button_rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
        button_rect.height = button_height
        button_rect.width = min(MENU_BUTTON_WIDTH, panel.width - 70)
        button_rect.center = (screen.get_width() // 2, min(panel.bottom - button_height // 2 - _scaled(20, scale, 12), second_field_y + input_height // 2 + gap_before_button + button_height // 2))
        draw_button(
            screen,
            button_rect,
            "Login" if mode == "login" else "Create Account",
            button_font,
            hovered=button_rect.collidepoint(mouse_pos),
            selected=True,
            enabled=not loading,
        )

        for idx, line in enumerate(_wrap_message(message)):
            color = RED if "wrong" in message.lower() or "not found" in message.lower() or "unavailable" in message.lower() or "already" in message.lower() else MUTED_TEXT
            draw_text(screen, line, message_font, color, screen.get_width() // 2, panel.bottom + _scaled(18, scale, 12) + idx * _scaled(16, scale, 12))
        if loading:
            draw_text(screen, "Please wait...", _scaled(18, scale, 13), WHITE, screen.get_width() // 2, min(height - bottom_margin, panel.bottom + message_area))
        else:
            draw_text(screen, "Use Exit from the main menu to quit", footer_font, MUTED_TEXT, screen.get_width() // 2, height - _scaled(18, scale, 12))

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
                    continue
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
    selected = 1
    while True:
        screen.fill(BLACK)
        panel = content_rect(screen, FORM_MAX_WIDTH, 250, y=105)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        draw_text(screen, title, 26, WHITE, panel.centerx, panel.y + 42)
        draw_text(screen, message[:44], 17, GRAY, panel.centerx, panel.y + 105)
        mouse_pos = pygame.mouse.get_pos()
        yes_rect = pygame.Rect(panel.centerx - 142, panel.y + 158, 120, 42)
        no_rect = pygame.Rect(panel.centerx + 22, panel.y + 158, 120, 42)
        draw_button(screen, yes_rect, "Yes", 20, hovered=yes_rect.collidepoint(mouse_pos), selected=selected == 0)
        draw_button(screen, no_rect, "No", 20, hovered=no_rect.collidepoint(mouse_pos), selected=selected == 1)
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    selected = 1 - selected
                elif event.key == pygame.K_y:
                    return True
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return selected == 0
                elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes_rect.collidepoint(event.pos):
                    return True
                if no_rect.collidepoint(event.pos):
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
        print(f"[auth-flow] Account error: {exc}")
        _message_screen(screen, clock, "Account error", normalize_auth_error(exc))


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
            profile_error = normalize_auth_error(error or "Could not refresh profile.")

    while True:
        screen.fill(BLACK)
        logged_in = state.account is not None and bool(state.account.access_token)
        draw_text_shadow(screen, "Profile", 36, WHITE, screen.get_width() // 2, 55)
        buttons: list[tuple[pygame.Rect, str]] = []

        if logged_in:
            nickname = state.account.username if state.account else ""
            reward = season_1_reward_for(nickname)
            summary = content_rect(screen, PROFILE_PANEL_MAX_WIDTH, 240, y=92)
            draw_panel(screen, summary, PANEL_BG, PANEL_BORDER)
            name_rect = draw_text(screen, nickname, 26, WHITE, summary.centerx, summary.y + 34)
            if reward is not None:
                draw_medal_badge(screen, reward, name_rect.right + 22, summary.y + 34, 13)
            if profile:
                rows = [
                    ("Season 1 Medal", reward.medal.title() if reward else "-"),
                    ("Best Score", str(profile.get("best_score", 0))),
                    ("Games Played", str(profile.get("games_played", 0))),
                    ("Season Rank", str(profile.get("current_season_rank") or "Unranked")),
                    ("Joined", _format_profile_date(profile.get("created_at"))),
                ]
            else:
                rows = [
                    ("Season 1 Medal", reward.medal.title() if reward else "-"),
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
                        if not _confirm(
                            screen,
                            clock,
                            "Log out?",
                            "Are you sure you want to log out?",
                        ):
                            return
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
                            print(f"[auth-flow] Nickname error: {exc}")
                            _message_screen(screen, clock, "Nickname error", normalize_auth_error(exc))
                    return
