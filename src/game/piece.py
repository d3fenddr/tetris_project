from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

import pygame


@dataclass
class Piece:
    shape: list[list[int]]
    x: int
    y: int

    @classmethod
    def spawn(
        cls,
        shapes: Sequence[list[list[int]]],
        weights: Sequence[int],
        cols: int,
    ) -> "Piece":
        idx = random.choices(range(len(shapes)), weights=weights, k=1)[0]
        shape = [row[:] for row in shapes[idx]]
        x = cols // 2 - len(shape[0]) // 2
        return cls(shape=shape, x=x, y=0)

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
        self.shape = new_shape
        if not self.valid_move(0, 0, grid, cols, rows):
            self.shape = old_shape

    def draw(
        self,
        screen: pygame.Surface,
        block_size: int,
        fill_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
    ) -> None:
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell:
                    rect = pygame.Rect(
                        (self.x + j) * block_size,
                        (self.y + i) * block_size,
                        block_size,
                        block_size,
                    )
                    pygame.draw.rect(screen, fill_color, rect)
                    pygame.draw.rect(screen, border_color, rect, 1)

