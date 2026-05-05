from __future__ import annotations

import queue
import threading
from datetime import datetime
from typing import Dict, List

import pygame

from src.config import BLACK, FPS, GRAY, RED, WHITE
from src.services.score_service import ScoreService
from src.state import AppState
from src.utils.date_utils import format_short_date, format_short_time, parse_sheet_datetime
from src.utils.ui_helpers import draw_text


def _load_history_worker(
    output: "queue.Queue[tuple[bool, List[Dict[str, str | int]], str]]",
    score_service: ScoreService,
    player_name: str,
) -> None:
    try:
        history = score_service.get_player_history(player_name)
        output.put((True, history, ""))
    except Exception as exc:  # Defensive catch for background thread only.
        output.put((False, [], str(exc)))


def show_history(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    score_service: ScoreService,
) -> None:
    per_page = 8
    page = 0
    sort_mode = "date"
    ascending = False

    loader_queue: "queue.Queue[tuple[bool, List[Dict[str, str | int]], str]]" = queue.Queue()
    loader_thread = threading.Thread(
        target=_load_history_worker,
        args=(loader_queue, score_service, state.player_name),
        daemon=True,
    )
    loader_thread.start()

    loading = True
    load_error = ""
    history: List[Dict[str, str | int]] = []

    def apply_sort(items: List[Dict[str, str | int]]) -> List[Dict[str, str | int]]:
        if sort_mode == "date":
            key = lambda row: _history_datetime(row)
        else:
            key = lambda row: int(row.get("score", 0))
        return sorted(items, key=key, reverse=not ascending)

    def _history_datetime(row: Dict[str, str | int]) -> datetime:
        raw = str(row.get("date") or row.get("created_at") or "")
        if "T" in raw:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return datetime.min
        return parse_sheet_datetime(raw) or datetime.min

    while True:
        if loading:
            try:
                success, loaded_data, error = loader_queue.get_nowait()
                loading = False
                history = loaded_data
                load_error = "" if success else (error or "Could not load history.")
            except queue.Empty:
                pass

        screen.fill(BLACK)
        if loading:
            draw_text(screen, "Loading history...", 28, WHITE, screen.get_width() // 2, screen.get_height() // 2 - 10)
            draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 30)
        elif load_error and not history:
            draw_text(screen, "History unavailable", 30, RED, screen.get_width() // 2, 110)
            draw_text(screen, load_error[:40], 18, GRAY, screen.get_width() // 2, 160)
            draw_text(screen, "Press R to retry", 20, WHITE, screen.get_width() // 2, 220)
            draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 30)
        else:
            filtered = apply_sort(history)
            pages = max(1, (len(filtered) + per_page - 1) // per_page)
            page = min(page, pages - 1)
            display = filtered[page * per_page : (page + 1) * per_page]

            draw_text(screen, f"Season 2 History: Page {page + 1}/{pages}", 24, WHITE, screen.get_width() // 2, 30)
            draw_text(screen, f"Total Games: {len(history)}", 20, GRAY, screen.get_width() // 2, 60)

            if not display:
                draw_text(screen, "No games found", 24, WHITE, screen.get_width() // 2, screen.get_height() // 2)
            else:
                history_by_date = sorted(
                    history,
                    key=_history_datetime,
                )
                game_index_map = {id(rec): idx + 1 for idx, rec in enumerate(history_by_date)}
                for idx, record in enumerate(display):
                    y = 100 + idx * 60
                    game_number = game_index_map.get(id(record), page * per_page + idx + 1)
                    draw_text(screen, f"Game {game_number}", 22, WHITE, screen.get_width() // 2 - 100, y)
                    draw_text(screen, f"Score: {int(record.get('score', 0))}", 20, WHITE, screen.get_width() // 2 - 100, y + 25)
                    date_value = str(record.get("date") or record.get("created_at") or "")
                    mode = str(record.get("mode", ""))
                    if "T" in date_value:
                        short_date = date_value[:10]
                        short_time = date_value[11:16]
                    else:
                        short_date = format_short_date(date_value)
                        short_time = format_short_time(date_value)
                    draw_text(screen, short_date, 16, GRAY, screen.get_width() // 2 + 60, y + 2)
                    draw_text(screen, f"{short_time} {mode}", 14, GRAY, screen.get_width() // 2 + 60, y + 23)

            draw_text(screen, "LEFT / RIGHT: Page", 20, GRAY, screen.get_width() // 2, screen.get_height() - 80)
            draw_text(screen, f"S - Sort with: {sort_mode}", 20, GRAY, screen.get_width() // 2, screen.get_height() - 55)
            draw_text(
                screen,
                f"F - Order: {'Up' if ascending else 'Down'}",
                20,
                GRAY,
                screen.get_width() // 2,
                screen.get_height() - 35,
            )
            draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 15)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if loading:
                    continue
                if event.key == pygame.K_r and load_error:
                    loading = True
                    load_error = ""
                    loader_thread = threading.Thread(
                        target=_load_history_worker,
                        args=(loader_queue, score_service, state.player_name),
                        daemon=True,
                    )
                    loader_thread.start()
                elif event.key == pygame.K_RIGHT:
                    page += 1
                elif event.key == pygame.K_LEFT:
                    page = max(0, page - 1)
                elif event.key == pygame.K_s:
                    sort_mode = "score" if sort_mode == "date" else "date"
                elif event.key == pygame.K_f:
                    ascending = not ascending
