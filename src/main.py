from __future__ import annotations

import os
from typing import Callable, Optional

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from src.assets import create_window, initialize_pygame, load_assets
from src.config import (
    BASE_MAX_VOLUME,
    GOOGLE_FIELD_NAME,
    GOOGLE_FIELD_SCORE,
    GOOGLE_FORM_URL,
    GOOGLE_SHEET_CSV_URL,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.game.gameplay import main_game
from src.services.account_service import AccountService
from src.services.backend_client import BackendClient
from src.services.google_sheet_service import GoogleSheetService
from src.services.score_service import ScoreService
from src.services.session_service import SessionService
from src.state import AppState
from src.ui.history import show_history
from src.ui.leaderboard import show_leaderboard, show_season1_top3
from src.ui.menu import ensure_player_name, show_game_mode_selector, show_main_menu
from src.ui.pause import pause_menu
from src.ui.profile import profile_screen
from src.ui.settings import settings_menu


def run() -> None:
    audio_available = initialize_pygame()
    screen = create_window()
    clock = pygame.time.Clock()

    if screen.get_width() != WINDOW_WIDTH or screen.get_height() != WINDOW_HEIGHT:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    assets, warnings = load_assets(audio_available)
    for warning in warnings:
        print(warning)

    session_service = SessionService()
    backend_client = BackendClient()
    score_service = ScoreService(
        google_service=GoogleSheetService(
            csv_url=GOOGLE_SHEET_CSV_URL,
            form_url=GOOGLE_FORM_URL,
            field_name=GOOGLE_FIELD_NAME,
            field_score=GOOGLE_FIELD_SCORE,
        ),
        session_service=session_service,
        backend_client=backend_client,
    )
    account_service = AccountService(session_service, backend_client)

    state = AppState.from_storage(session_service.load())
    saved_account = account_service.load_account()
    if saved_account:
        user = account_service.refresh_current_user()
        state.account = account_service.load_account()
        if state.account:
            state.player_name = state.account.username

    def persist_state() -> None:
        session_service.update_state(state.to_storage())
        if state.account:
            account_service.save_account(state.account)

    def apply_volume() -> None:
        if not assets.audio_available:
            return
        if state.music_enabled:
            volume = (state.volume_percent / 100) * BASE_MAX_VOLUME
        else:
            volume = 0
        pygame.mixer.music.set_volume(volume)

    current_music = {"path": ""}

    def play_music(path: str) -> None:
        if not assets.audio_available:
            return
        if current_music["path"] == path and pygame.mixer.music.get_busy():
            return
        try:
            pygame.mixer.music.load(path)
            apply_volume()
            pygame.mixer.music.play(-1)
            current_music["path"] = path
        except pygame.error as exc:
            print(f"Music load failed: {path} ({exc})")

    def pause_music() -> None:
        if assets.audio_available:
            pygame.mixer.music.pause()

    def unpause_music() -> None:
        if assets.audio_available:
            pygame.mixer.music.unpause()

    def stop_music() -> None:
        if assets.audio_available:
            pygame.mixer.music.stop()
            current_music["path"] = ""

    ensure_player_name(screen, clock, state, assets.first_page_img)
    persist_state()

    while True:
        play_music(assets.menu_music_path)
        action = show_main_menu(screen, clock, state, assets.background_img)
        persist_state()

        if action == "play":
            selected_mode = show_game_mode_selector(screen, clock, state, assets.background_img)
            if selected_mode is None:
                continue
            state.game_mode = selected_mode
            persist_state()
            stop_music()
            play_music(assets.game_music_path)

            def open_settings() -> None:
                settings_menu(screen, clock, state, apply_volume, persist_state)

            def open_pause(draw_frame: Callable[[], None], score: int) -> Optional[str]:
                return pause_menu(
                    screen=screen,
                    clock=clock,
                    draw_game_frame=draw_frame,
                    score=score,
                    open_settings_menu=open_settings,
                    on_pause_music=pause_music,
                    on_unpause_music=unpause_music,
                    on_stop_music=stop_music,
                )

            main_game(
                screen=screen,
                clock=clock,
                state=state,
                background_img=assets.background_img,
                score_service=score_service,
                open_pause_menu=open_pause,
                on_game_over=stop_music,
            )
        elif action == "history":
            show_history(screen, clock, state, score_service)
        elif action == "profile":
            profile_screen(screen, clock, state, account_service, persist_state)
        elif action == "season 1 top 3":
            show_season1_top3(screen, clock, score_service)
        elif action == "settings":
            settings_menu(screen, clock, state, apply_volume, persist_state)
        elif action == "leaderboard":
            show_leaderboard(screen, clock, score_service)
        elif action == "exit":
            persist_state()
            break

    stop_music()
    pygame.quit()


if __name__ == "__main__":
    run()
