from __future__ import annotations

from typing import Callable

import pygame

from src.config import BLACK, BUTTON_DEBOUNCE_MS, FPS, GRAY, RED, WHITE
from src.services.account_service import AccountService
from src.services.backend_client import BackendClientError
from src.state import AppState
from src.utils.ui_helpers import draw_text


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
        draw_text(screen, "Profile", 36, WHITE, screen.get_width() // 2, 55)
        buttons: list[tuple[pygame.Rect, str]] = []

        if logged_in:
            nickname = state.account.username if state.account else ""
            draw_text(screen, f"Nickname: {nickname}", 24, WHITE, screen.get_width() // 2, 125)
            if profile:
                draw_text(screen, f"Best: {profile.get('best_score', 0)}", 20, GRAY, screen.get_width() // 2, 165)
                draw_text(screen, f"Games: {profile.get('games_played', 0)}", 20, GRAY, screen.get_width() // 2, 195)
            options = [("Change Nickname", "change"), ("Logout", "logout")]
        else:
            draw_text(screen, "You are playing as guest.", 22, GRAY, screen.get_width() // 2, 130)
            draw_text(screen, "Log in to submit Season 2 scores.", 17, GRAY, screen.get_width() // 2, 160)
            options = [("Login", "login"), ("Register", "register")]

        mx, my = pygame.mouse.get_pos()
        for idx, (label, action) in enumerate(options):
            y = 280 + idx * 58
            font = pygame.font.SysFont("comicsans", 26)
            surface = font.render(label, True, RED if abs(my - y) < 22 else WHITE)
            rect = surface.get_rect(center=(screen.get_width() // 2, y))
            screen.blit(surface, rect)
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
