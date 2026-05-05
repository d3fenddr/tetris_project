from __future__ import annotations

import queue
import threading
from typing import Any, List, Tuple

import pygame

from src.config import (
    BLACK,
    BRONZE,
    CURRENT_SEASON,
    FPS,
    GOLD,
    GRAY,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    RED,
    SILVER,
    WHITE,
)
from src.game.modes import game_mode_label
from src.services.score_service import ScoreService
from src.utils.ui_helpers import draw_button, draw_panel, draw_text, draw_text_shadow


LEADERBOARD_TABS = [
    ("all", "All"),
    ("peaceful", "Peaceful"),
    ("easy", "Easy"),
    ("normal", "Normal"),
    ("hard", "Hard"),
]


def _load_leaderboard_worker(
    output: "queue.Queue[tuple[str, bool, List[dict[str, Any]], str]]",
    score_service: ScoreService,
    mode: str,
) -> None:
    try:
        leaderboard = score_service.get_leaderboard(mode=None if mode == "all" else mode)
        output.put((mode, True, leaderboard, ""))
    except Exception as exc:
        output.put((mode, False, [], str(exc)))


def _load_season1_worker(
    output: "queue.Queue[tuple[bool, List[Tuple[str, Tuple[int, str]]], str]]",
    score_service: ScoreService,
) -> None:
    try:
        leaderboard = score_service.get_season1_top3()
        output.put((True, leaderboard, ""))
    except Exception as exc:
        output.put((False, [], str(exc)))


def show_leaderboard(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    score_service: ScoreService,
) -> None:
    loader_queue: "queue.Queue[tuple[str, bool, List[dict[str, Any]], str]]" = queue.Queue()

    loading = True
    load_error = ""
    leaderboard: List[dict[str, Any]] = []
    colors = [GOLD, SILVER, BRONZE]
    active_tab = 0
    last_click_ms = 0

    def load_active_tab() -> None:
        nonlocal loading, load_error, leaderboard
        loading = True
        load_error = ""
        leaderboard = []
        mode = LEADERBOARD_TABS[active_tab][0]
        threading.Thread(
            target=_load_leaderboard_worker,
            args=(loader_queue, score_service, mode),
            daemon=True,
        ).start()

    load_active_tab()

    while True:
        if loading:
            try:
                loaded_mode, success, loaded, error = loader_queue.get_nowait()
                if loaded_mode != LEADERBOARD_TABS[active_tab][0]:
                    continue
                loading = False
                leaderboard = loaded
                load_error = "" if success else (error or "Online leaderboard is unavailable.")
            except queue.Empty:
                pass

        screen.fill(BLACK)
        draw_text_shadow(screen, f"Season {CURRENT_SEASON} Leaderboard", 28, WHITE, screen.get_width() // 2, 34)

        mouse_pos = pygame.mouse.get_pos()
        tab_rects: list[tuple[int, pygame.Rect]] = []
        tab_width = 62
        start_x = screen.get_width() // 2 - (tab_width * len(LEADERBOARD_TABS)) // 2
        for idx, (_mode, label) in enumerate(LEADERBOARD_TABS):
            rect = pygame.Rect(start_x + idx * tab_width, 72, tab_width - 5, 32)
            draw_button(
                screen,
                rect,
                label,
                13,
                hovered=rect.collidepoint(mouse_pos),
                selected=idx == active_tab,
            )
            tab_rects.append((idx, rect))

        if loading:
            draw_text(screen, "Loading...", 28, WHITE, screen.get_width() // 2, screen.get_height() // 2 - 20)
        elif load_error and not leaderboard:
            draw_text(screen, "Online leaderboard unavailable", 24, RED, screen.get_width() // 2, 110)
            draw_text(screen, load_error[:42], 16, GRAY, screen.get_width() // 2, 148)
            draw_text(screen, "Press R to retry", 20, WHITE, screen.get_width() // 2, 205)
        elif not leaderboard:
            empty = "Season 2 leaderboard is empty." if LEADERBOARD_TABS[active_tab][0] == "all" else "No scores yet for this mode."
            draw_text(screen, empty, 23, WHITE, screen.get_width() // 2, 180)
        else:
            for idx, row in enumerate(leaderboard[:10]):
                y = 130 + idx * 50
                color = colors[idx] if idx < 3 else WHITE
                rank = int(row.get("rank", idx + 1))
                nickname = str(row.get("nickname", "unknown"))
                score = int(row.get("score", 0))
                mode = str(row.get("mode", "")).lower()
                lines = int(row.get("lines", 0))
                row_rect = pygame.Rect(18, y - 22, screen.get_width() - 36, 43)
                draw_panel(screen, row_rect, PANEL_BG, PANEL_BORDER, radius=7)
                draw_text(screen, f"{rank}. {nickname}", 18, color, row_rect.x + 72, y - 5)
                draw_text(screen, str(score), 18, WHITE, row_rect.right - 54, y - 5)
                mode_label = game_mode_label(mode) if mode else "Unknown"
                draw_text(screen, f"{mode_label} | lines {lines}", 12, MUTED_TEXT, row_rect.centerx, y + 13)

        draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_r and load_error:
                    load_active_tab()
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    active_tab = (active_tab + 1) % len(LEADERBOARD_TABS)
                    load_active_tab()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    active_tab = (active_tab - 1) % len(LEADERBOARD_TABS)
                    load_active_tab()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < 120:
                    continue
                last_click_ms = now
                for idx, rect in tab_rects:
                    if rect.collidepoint(event.pos) and idx != active_tab:
                        active_tab = idx
                        load_active_tab()
                        break


def show_season1_top3(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    score_service: ScoreService,
) -> None:
    loader_queue: "queue.Queue[tuple[bool, List[Tuple[str, Tuple[int, str]]], str]]" = queue.Queue()
    threading.Thread(target=_load_season1_worker, args=(loader_queue, score_service), daemon=True).start()

    loading = True
    load_error = ""
    winners: List[Tuple[str, Tuple[int, str]]] = []
    colors = [GOLD, SILVER, BRONZE]

    while True:
        if loading:
            try:
                success, loaded, error = loader_queue.get_nowait()
                loading = False
                winners = loaded
                load_error = "" if success else (error or "Season 1 leaderboard is unavailable right now.")
            except queue.Empty:
                pass

        screen.fill(BLACK)
        draw_text_shadow(screen, "Season 1 Top 3", 34, WHITE, screen.get_width() // 2, 56)

        if loading:
            draw_text(screen, "Loading archived winners...", 24, WHITE, screen.get_width() // 2, 180)
        elif load_error and not winners:
            draw_text(screen, "Season 1 leaderboard is unavailable right now.", 20, RED, screen.get_width() // 2, 180)
        elif not winners:
            draw_text(screen, "No Season 1 winners found.", 22, WHITE, screen.get_width() // 2, 180)
        else:
            labels = ["1st", "2nd", "3rd"]
            for idx, (name, (score, _date)) in enumerate(winners[:3]):
                y = 170 + idx * 90
                rect = pygame.Rect(35, y - 32, screen.get_width() - 70, 70)
                draw_panel(screen, rect, PANEL_BG, PANEL_BORDER)
                draw_text(screen, labels[idx], 23, colors[idx], screen.get_width() // 2, y - 9)
                draw_text(screen, f"{name}: {score}", 21, WHITE, screen.get_width() // 2, y + 18)

        draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
