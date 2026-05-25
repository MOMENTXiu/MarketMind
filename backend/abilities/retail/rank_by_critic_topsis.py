"""CRITIC weighting and TOPSIS ranking abilities for Retail V2."""

from __future__ import annotations

import numpy as np


def minmax_normalize(
    matrix: np.ndarray,
    benefit: list[bool] | None = None,
    eps: float = 1e-12,
) -> np.ndarray:
    """Normalize metric columns to [0, 1] while respecting benefit direction."""

    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2:
        raise ValueError("matrix must be a 2-dimensional array")
    if benefit is None:
        benefit = [True] * values.shape[1]

    normalized = np.zeros_like(values, dtype=float)
    for index in range(values.shape[1]):
        column = values[:, index]
        low = np.nanmin(column)
        high = np.nanmax(column)
        if high - low < eps:
            normalized[:, index] = 0.0
        elif benefit[index]:
            normalized[:, index] = (column - low) / (high - low + eps)
        else:
            normalized[:, index] = (high - column) / (high - low + eps)
    return normalized


def critic_weights(
    matrix: np.ndarray,
    benefit: list[bool] | None = None,
    eps: float = 1e-12,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Compute CRITIC metric weights."""

    normalized = minmax_normalize(matrix, benefit, eps)
    if normalized.shape[1] == 1:
        weights = np.array([1.0])
        return weights, {
            "std": np.array([0.0]),
            "conflict": np.array([1.0]),
            "information": np.array([1.0]),
        }

    standard_deviation = normalized.std(axis=0, ddof=1)
    correlation = np.corrcoef(normalized, rowvar=False)
    correlation = np.nan_to_num(correlation, nan=0.0)
    conflict = np.sum(1.0 - correlation, axis=1)
    information = standard_deviation * conflict
    if information.sum() <= eps:
        weights = np.ones(normalized.shape[1]) / normalized.shape[1]
    else:
        weights = information / (information.sum() + eps)
    return weights, {
        "std": standard_deviation,
        "conflict": conflict,
        "information": information,
    }


def topsis(
    matrix: np.ndarray,
    weights: np.ndarray | None = None,
    benefit: list[bool] | None = None,
    eps: float = 1e-12,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Rank rows with TOPSIS closeness scores."""

    values = np.asarray(matrix, dtype=float)
    if benefit is None:
        benefit = [True] * values.shape[1]
    if weights is None:
        weights, _ = critic_weights(values, benefit, eps)

    normalized = minmax_normalize(values, benefit, eps)
    weighted = normalized * weights
    ideal_positive = weighted.max(axis=0)
    ideal_negative = weighted.min(axis=0)
    positive_distance = np.sqrt(((weighted - ideal_positive) ** 2).sum(axis=1))
    negative_distance = np.sqrt(((weighted - ideal_negative) ** 2).sum(axis=1))
    closeness = negative_distance / (positive_distance + negative_distance + eps)
    return closeness, {
        "positive_distance": positive_distance,
        "negative_distance": negative_distance,
        "weights": weights,
        "ideal_positive": ideal_positive,
        "ideal_negative": ideal_negative,
    }
