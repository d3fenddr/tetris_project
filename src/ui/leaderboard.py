from __future__ import annotations

import queue
import threading
from typing import Any, List, Tuple

import pygame

from src.config import BLACK, BRONZE, CURRENT_SEASON, FPS, GOLD, GRAY, RED, SILVER, WHITE
from src.services.score_service import ScoreService
from src.utils.ui_helpers import draw_text


def _load_leaderboard_worker(
    output: "queue.Queue[tuple[bool, List[dict[str, Any]], str]]",
    score_service: ScoreService,
) -> None:
    try:
        leaderboard = score_service.get_leaderboard()
        output.put((True, leaderboard, ""))
    except Exception as exc:
        output.put((False, [], str(exc)))


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
    loader_queue: "queue.Queue[tuple[bool, List[dict[str, Any]], str]]" = queue.Queue()
    loader_thread = threading.Thread(target=_load_leaderboard_worker, args=(loader_queue, score_service), daemon=True)
    loader_thread.start()

    loading = True
    load_error = ""
    leaderboard: List[dict[str, Any]] = []
    colors = [GOLD, SILVER, BRONZE]

    while True:
        if loading:
            try:
                success, loaded, error = loader_queue.get_nowait()
                loading = False
                leaderboard = loaded
                load_error = "" if success else (error or "Online leaderboard is unavailable.")
            except queue.Empty:
                pass

        screen.fill(BLACK)
        draw_text(screen, f"Season {CURRENT_SEASON} Leaderboard", 30, WHITE, screen.get_width() // 2, 32)

        if loading:
            draw_text(screen, "Loading...", 28, WHITE, screen.get_width() // 2, screen.get_height() // 2 - 20)
        elif load_error and not leaderboard:
            draw_text(screen, "Online leaderboard unavailable", 24, RED, screen.get_width() // 2, 110)
            draw_text(screen, load_error[:42], 16, GRAY, screen.get_width() // 2, 148)
            draw_text(screen, "Press R to retry", 20, WHITE, screen.get_width() // 2, 205)
        elif not leaderboard:
            draw_text(screen, "Season 2 leaderboard is empty.", 24, WHITE, screen.get_width() // 2, 180)
        else:
            for idx, row in enumerate(leaderboard[:10]):
                y = 82 + idx * 58
                color = colors[idx] if idx < 3 else WHITE
                rank = int(row.get("rank", idx + 1))
                nickname = str(row.get("nickname", "unknown"))
                score = int(row.get("score", 0))
                mode = str(row.get("mode", ""))
                lines = int(row.get("lines", 0))
                draw_text(screen, f"{rank}. {nickname}: {score}", 22, color, screen.get_width() // 2, y)
                draw_text(screen, f"{mode} | lines {lines}", 15, GRAY, screen.get_width() // 2, y + 22)

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
                    loading = True
                    load_error = ""
                    loader_thread = threading.Thread(
                        target=_load_leaderboard_worker,
                        args=(loader_queue, score_service),
                        daemon=True,
                    )
                    loader_thread.start()


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
        draw_text(screen, "Season 1 Top 3", 34, WHITE, screen.get_width() // 2, 56)

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
                draw_text(screen, labels[idx], 26, colors[idx], screen.get_width() // 2, y)
                draw_text(screen, f"{name}: {score}", 24, WHITE, screen.get_width() // 2, y + 34)

        draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
