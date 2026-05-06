from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeasonReward:
    username: str
    rank: int
    medal: str


SEASON_1_REWARDS: tuple[SeasonReward, ...] = (
    SeasonReward(username="emin", rank=1, medal="gold"),
    SeasonReward(username="karimlox2005", rank=2, medal="silver"),
    SeasonReward(username="OLEGSREDA", rank=3, medal="bronze"),
)


def normalize_username(username: str) -> str:
    return username.strip().casefold()


def season_1_reward_for(username: str) -> SeasonReward | None:
    normalized = normalize_username(username)
    for reward in SEASON_1_REWARDS:
        if normalize_username(reward.username) == normalized:
            return reward
    return None
