from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

import pygame

from src.config import ACTIVE_PIECE_COLORS


@dataclass
class Piece:
    shape: list[list[int]]
    x: int
    y: int
    color: tuple[int, int, int]

    @classmethod
    def spawn(
        cls,
        shapes: Sequence[list[list[int]]],
        weights: Sequence[float],
        cols: int,
    ) -> "Piece":
        idx = random.choices(range(len(shapes)), weights=weights, k=1)[0]
        shape = [row[:] for row in shapes[idx]]
        x = cols // 2 - len(shape[0]) // 2
        color = random.choice(ACTIVE_PIECE_COLORS)
        return cls(shape=shape, x=x, y=0, color=color)

    def get_cells(self) -> list[tuple[int, int]]:
        return [
            (self.x + j, self.y + i)
            for i, row in enumerate(self.shape)
            for j, cell in enumerate(row)
            if cell
        ]

    def valid_move(self, dx: int, dy: int, grid: list[list[int]], cols: int, rows: int) -> bool:
        for x, y in self.get_cells():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= cols or ny >= rows:
                return False
            if ny >= 0 and grid[ny][nx]:
                return False
        return True

    def rotate(self, grid: list[list[int]], cols: int, rows: int) -> None:
        new_shape = [list(row) for row in zip(*self.shape[::-1])]
        old_shape = self.shape
        old_x = self.x
        old_y = self.y
        self.shape = new_shape
        for kick_x, kick_y in ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)):
            self.x = old_x + kick_x
            self.y = old_y + kick_y
            if self.valid_move(0, 0, grid, cols, rows):
                return
        self.shape = old_shape
        self.x = old_x
        self.y = old_y

    def draw_preview(
        self,
        screen: pygame.Surface,
        block_size: int,
        preview_rect: pygame.Rect,
        border_color: tuple[int, int, int],
    ) -> None:
        occupied = [
            (j, i)
            for i, row in enumerate(self.shape)
            for j, cell in enumerate(row)
            if cell
        ]
        if not occupied:
            return
        min_x = min(x for x, _y in occupied)
        max_x = max(x for x, _y in occupied)
        min_y = min(y for _x, y in occupied)
        max_y = max(y for _x, y in occupied)
        shape_width = (max_x - min_x + 1) * block_size
        shape_height = (max_y - min_y + 1) * block_size
        start_x = preview_rect.x + (preview_rect.width - shape_width) // 2
        start_y = preview_rect.y + (preview_rect.height - shape_height) // 2
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if not cell:
                    continue
                rect = pygame.Rect(
                    start_x + (j - min_x) * block_size,
                    start_y + (i - min_y) * block_size,
                    block_size,
                    block_size,
                )
                pygame.draw.rect(screen, self.color, rect)
                pygame.draw.rect(screen, border_color, rect, 1)

    def draw(
        self,
        screen: pygame.Surface,
        block_size: int,
        fill_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell:
                    rect = pygame.Rect(
                        offset_x + (self.x + j) * block_size,
                        offset_y + (self.y + i) * block_size,
                        block_size,
                        block_size,
                    )
                    pygame.draw.rect(screen, self.color or fill_color, rect)
                    pygame.draw.rect(screen, border_color, rect, 1)
