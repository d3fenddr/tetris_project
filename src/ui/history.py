from __future__ import annotations

import queue
import threading
from datetime import datetime
from typing import Dict, List

import pygame

from src.config import BLACK, FPS, HISTORY_PANEL_MAX_WIDTH, MUTED_TEXT, PANEL_BG, PANEL_BORDER, RED, WHITE
from src.game.modes import game_mode_label
from src.services.score_service import ScoreService
from src.state import AppState
from src.utils.date_utils import format_short_date, format_short_time, parse_sheet_datetime
from src.utils.layout import content_rect, handle_resize_event
from src.utils.ui_helpers import draw_panel, draw_text, draw_text_shadow


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
        draw_text_shadow(screen, "Season 2 History", 30, WHITE, screen.get_width() // 2, 38)
        if loading:
            panel = content_rect(screen, HISTORY_PANEL_MAX_WIDTH, 150, y=220)
            draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
            draw_text(screen, "Loading history...", 24, WHITE, panel.centerx, panel.centery - 8)
            draw_text(screen, "Fetching Season 2 games", 15, MUTED_TEXT, panel.centerx, panel.centery + 26)
            draw_text(screen, "ESC to return", 17, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 24)
        elif load_error and not history:
            panel = content_rect(screen, HISTORY_PANEL_MAX_WIDTH, 210, y=145)
            draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
            draw_text(screen, "History unavailable", 25, RED, panel.centerx, panel.y + 48)
            draw_text(screen, load_error[:40], 15, MUTED_TEXT, panel.centerx, panel.y + 88)
            draw_text(screen, "Press R to retry", 18, WHITE, panel.centerx, panel.y + 142)
            draw_text(screen, "ESC to return", 17, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 24)
        else:
            filtered = apply_sort(history)
            pages = max(1, (len(filtered) + per_page - 1) // per_page)
            page = min(page, pages - 1)
            display = filtered[page * per_page : (page + 1) * per_page]

            best_score = max((int(item.get("score", 0)) for item in history), default=0)
            stat_panel = content_rect(screen, HISTORY_PANEL_MAX_WIDTH, 58, y=68)
            draw_panel(screen, stat_panel, PANEL_BG, PANEL_BORDER)
            draw_text(screen, f"Games: {len(history)}", 16, WHITE, stat_panel.x + 76, stat_panel.centery - 7)
            draw_text(screen, f"Best: {best_score}", 16, WHITE, stat_panel.centerx, stat_panel.centery - 7)
            draw_text(screen, f"Page {page + 1}/{pages}", 16, WHITE, stat_panel.right - 72, stat_panel.centery - 7)
            draw_text(
                screen,
                f"Sort: {sort_mode} | {'Oldest first' if ascending else 'Newest first'}",
                12,
                MUTED_TEXT,
                stat_panel.centerx,
                stat_panel.centery + 16,
            )

            if not display:
                draw_text(screen, "No games found", 24, WHITE, screen.get_width() // 2, screen.get_height() // 2)
            else:
                history_by_date = sorted(
                    history,
                    key=_history_datetime,
                )
                game_index_map = {id(rec): idx + 1 for idx, rec in enumerate(history_by_date)}
                for idx, record in enumerate(display):
                    y = 158 + idx * 58
                    game_number = game_index_map.get(id(record), page * per_page + idx + 1)
                    row_rect = content_rect(screen, HISTORY_PANEL_MAX_WIDTH, 48, y=y - 24)
                    draw_panel(screen, row_rect, PANEL_BG, PANEL_BORDER, radius=7)
                    draw_text(screen, f"Game {game_number}", 15, MUTED_TEXT, row_rect.x + 57, y - 8)
                    draw_text(screen, f"{int(record.get('score', 0))}", 20, WHITE, row_rect.x + 60, y + 12)
                    date_value = str(record.get("date") or record.get("created_at") or "")
                    mode = str(record.get("mode", ""))
                    if "T" in date_value:
                        short_date = date_value[:10]
                        short_time = date_value[11:16]
                    else:
                        short_date = format_short_date(date_value)
                        short_time = format_short_time(date_value)
                    mode_text = game_mode_label(mode) if mode else "Unknown"
                    draw_text(screen, short_date, 13, MUTED_TEXT, row_rect.right - 68, y - 8)
                    draw_text(screen, f"{short_time} | {mode_text}", 12, MUTED_TEXT, row_rect.right - 68, y + 13)

            draw_text(screen, "LEFT/RIGHT page   S sort   F order   ESC back", 13, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 20)

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
