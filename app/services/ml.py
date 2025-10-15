from __future__ import annotations
from typing import List
import math

try:
    import numpy as np
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False
    np = None
    LinearRegression = None

from app.models import YieldPool


async def forecast_7d(pools: List[YieldPool], history: List[List[float]] | None = None) -> None:
    """
    Lightweight forecast: per pool, fit linear model on last N APY points (if provided via history)
    and project 7 days ahead. If no history, leave predicted_apy as None.
    This function mutates the `pools` list items.
    """
    if not SKLEARN_AVAILABLE or not history:
        return

    # history: list aligned to pools order; each element is a list of recent daily APYs (in %)
    for pool, series in zip(pools, history):
        if not series or len(series) < 3:
            continue
        # Prepare X as day indices, y as apy
        X = np.arange(len(series)).reshape(-1, 1)
        y = np.array(series)
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(np.array([[len(series) + 7]]) )[0]
        pool.predicted_apy = float(max(0.0, pred))
