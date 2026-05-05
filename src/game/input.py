from __future__ import annotations

from typing import Callable, Dict

import pygame

from src.config import (
    KEY_REPEAT_INITIAL_DELAY_MS,
    KEY_REPEAT_MOVE_INTERVAL_MS,
    KEY_REPEAT_SOFT_DROP_INTERVAL_MS,
)


RepeatAction = Callable[[], None]


class KeyRepeatController:
    def __init__(self, actions: Dict[int, RepeatAction]) -> None:
        self.actions = actions
        self._next_repeat_at: Dict[int, int] = {}

    def press(self, key: int, now_ms: int) -> bool:
        action = self.actions.get(key)
        if action is None:
            return False
        if key in self._next_repeat_at:
            return True

        action()
        self._next_repeat_at[key] = now_ms + KEY_REPEAT_INITIAL_DELAY_MS
        return True

    def release(self, key: int) -> None:
        self._next_repeat_at.pop(key, None)

    def update(self, now_ms: int) -> None:
        for key, next_repeat_at in list(self._next_repeat_at.items()):
            action = self.actions.get(key)
            if action is None:
                self.release(key)
                continue
            if now_ms < next_repeat_at:
                continue

            action()
            interval = (
                KEY_REPEAT_SOFT_DROP_INTERVAL_MS
                if key == pygame.K_DOWN
                else KEY_REPEAT_MOVE_INTERVAL_MS
            )
            self._next_repeat_at[key] = now_ms + interval

    def clear(self) -> None:
        self._next_repeat_at.clear()
