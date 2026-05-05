from __future__ import annotations

from typing import Any, Dict, List

from src.config import (
    DEFAULT_GAME_MODE,
    DEFAULT_PIECE_WEIGHT,
    GAME_MODE_CONFIGS,
    GAME_MODE_ORDER,
    SHAPE_NAMES,
    SHAPES,
)


def validated_game_mode(mode: str | None) -> str:
    if mode in GAME_MODE_CONFIGS:
        return str(mode)
    print(f"Invalid game mode configured: {mode!r}. Falling back to {DEFAULT_GAME_MODE}.")
    return DEFAULT_GAME_MODE


def game_mode_label(mode: str | None) -> str:
    config = GAME_MODE_CONFIGS[validated_game_mode(mode)]
    return str(config["label"])


def game_mode_description(mode: str | None) -> str:
    config = GAME_MODE_CONFIGS[validated_game_mode(mode)]
    return str(config["description"])


def next_game_mode(current_mode: str | None, direction: int) -> str:
    current = validated_game_mode(current_mode)
    index = GAME_MODE_ORDER.index(current)
    return GAME_MODE_ORDER[(index + direction) % len(GAME_MODE_ORDER)]


def piece_weights_for_mode(mode: str | None) -> List[float]:
    clean_mode = validated_game_mode(mode)
    config: Dict[str, Any] = GAME_MODE_CONFIGS[clean_mode]

    if len(SHAPE_NAMES) != len(SHAPES):
        print("SHAPE_NAMES and SHAPES are out of sync. Falling back to default piece weights.")
        return [float(DEFAULT_PIECE_WEIGHT)] * len(SHAPES)

    valid_piece_names = set(SHAPE_NAMES)
    weights_by_piece = {name: float(DEFAULT_PIECE_WEIGHT) for name in SHAPE_NAMES}

    for piece_name in config.get("excluded_pieces", []):
        if piece_name not in valid_piece_names:
            print(f"Invalid excluded piece {piece_name!r} in {game_mode_label(clean_mode)} mode.")
            continue
        weights_by_piece[piece_name] = 0

    for piece_name, weight in dict(config.get("weights", {})).items():
        if piece_name not in valid_piece_names:
            print(f"Invalid weighted piece {piece_name!r} in {game_mode_label(clean_mode)} mode.")
            continue
        try:
            parsed_weight = float(weight)
        except (TypeError, ValueError):
            print(f"Invalid weight {weight!r} for piece {piece_name!r} in {game_mode_label(clean_mode)} mode.")
            continue
        if parsed_weight <= 0:
            print(f"Invalid non-positive weight {parsed_weight!r} for piece {piece_name!r}.")
            continue
        weights_by_piece[piece_name] = parsed_weight

    weights = [weights_by_piece[name] for name in SHAPE_NAMES]
    if sum(weights) <= 0:
        print(f"{game_mode_label(clean_mode)} mode has no spawnable pieces. Falling back to defaults.")
        return [float(DEFAULT_PIECE_WEIGHT)] * len(SHAPES)

    return weights
