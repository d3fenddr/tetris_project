from __future__ import annotations

from typing import Dict, Tuple


def create_grid(
    locked: Dict[Tuple[int, int], int] | None,
    rows: int,
    cols: int,
) -> list[list[int]]:
    locked = locked or {}
    grid = [[0] * cols for _ in range(rows)]
    for (x, y), value in locked.items():
        if 0 <= x < cols and 0 <= y < rows:
            grid[y][x] = value
    return grid


def clear_full_rows(
    locked: Dict[Tuple[int, int], int],
    rows: int,
    cols: int,
) -> tuple[Dict[Tuple[int, int], int], int]:
    grid = create_grid(locked, rows, cols)
    full_rows = [y for y in range(rows) if all(grid[y][x] for x in range(cols))]
    if not full_rows:
        return locked, 0

    for row in full_rows:
        for x in range(cols):
            locked.pop((x, row), None)

    new_locked: Dict[Tuple[int, int], int] = {}
    for (x, y), value in locked.items():
        shift = sum(1 for full_y in full_rows if y < full_y)
        new_locked[(x, y + shift)] = value
    return new_locked, len(full_rows)

