"""Shared generation context: deterministic RNG plus profile config."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np

from data_generator.config.profiles import ProfileConfig


@dataclass
class GenContext:
    cfg: ProfileConfig
    seed: int
    today: date = date(2026, 7, 1)  # fixed anchor keeps output deterministic
    rng: np.random.Generator = field(init=False)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.seed)

    # -- small helpers -------------------------------------------------------
    def choice(self, items: list, size: int | None = None, p: list[float] | None = None) -> Any:
        return self.rng.choice(items, size=size, p=p)

    def weighted_keys(self, weights: dict[str, float], size: int) -> np.ndarray:
        keys = list(weights.keys())
        w = np.array(list(weights.values()), dtype=float)
        return self.rng.choice(keys, size=size, p=w / w.sum())

    def past_date(self, max_days: int, min_days: int = 0) -> date:
        return self.today - timedelta(days=int(self.rng.integers(min_days, max_days + 1)))

    def past_dates(self, n: int, max_days: int, min_days: int = 0) -> list[date]:
        offsets = self.rng.integers(min_days, max_days + 1, size=n)
        return [self.today - timedelta(days=int(o)) for o in offsets]

    def future_dates(self, n: int, max_days: int, min_days: int = 1) -> list[date]:
        offsets = self.rng.integers(min_days, max_days + 1, size=n)
        return [self.today + timedelta(days=int(o)) for o in offsets]
