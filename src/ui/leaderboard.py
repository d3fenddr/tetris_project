from __future__ import annotations

import queue
import threading
from typing import List, Tuple

import pygame

from src.config import BLACK, BRONZE, FPS, GOLD, GRAY, RED, SILVER, WHITE
from src.services.score_service import ScoreService
from src.utils.date_utils import format_short_date, format_short_time
from src.utils.ui_helpers import draw_text


def _load_leaderboard_worker(
    output: "queue.Queue[tuple[bool, List[Tuple[str, Tuple[int, str]]], str]]",
    score_service: ScoreService,
) -> None:
    try:
        leaderboard = score_service.get_leaderboard()
        output.put((True, leaderboard, ""))
    except Exception as exc:  # Defensive catch for background thread only.
        output.put((False, [], str(exc)))


def show_leaderboard(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    score_service: ScoreService,
) -> None:
    loader_queue: "queue.Queue[tuple[bool, List[Tuple[str, Tuple[int, str]]], str]]" = queue.Queue()
    loader_thread = threading.Thread(target=_load_leaderboard_worker, args=(loader_queue, score_service), daemon=True)
    loader_thread.start()

    loading = True
    load_error = ""
    leaderboard: List[Tuple[str, Tuple[int, str]]] = []
    colors = [GOLD, SILVER, BRONZE]
    sizes = [28, 26, 24]

    while True:
        if loading:
            try:
                success, loaded, error = loader_queue.get_nowait()
                loading = False
                leaderboard = loaded
                load_error = "" if success else (error or "Could not load leaderboard.")
            except queue.Empty:
                pass

        screen.fill(BLACK)
        draw_text(screen, "Leaderboard", 36, WHITE, screen.get_width() // 2, 30)

        if loading:
            draw_text(screen, "Loading...", 28, WHITE, screen.get_width() // 2, screen.get_height() // 2 - 20)
            draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        elif load_error and not leaderboard:
            draw_text(screen, "Leaderboard unavailable", 28, RED, screen.get_width() // 2, 100)
            draw_text(screen, load_error[:40], 18, GRAY, screen.get_width() // 2, 145)
            draw_text(screen, "Press R to retry", 20, WHITE, screen.get_width() // 2, 205)
            draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        else:
            for idx, (name, (score, date)) in enumerate(leaderboard[:10]):
                y = 80 + idx * 70
                color = colors[idx] if idx < 3 else WHITE
                size = sizes[idx] if idx < 3 else 22
                draw_text(screen, f"{idx + 1}. {name}: {score}", size, color, screen.get_width() // 2, y)
                draw_text(
                    screen,
                    f"{format_short_date(date)} {format_short_time(date)}",
                    16,
                    GRAY,
                    screen.get_width() // 2,
                    y + 20,
                )
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

