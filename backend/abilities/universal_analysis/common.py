"""Common utilities for universal analysis abilities."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def positive(df: pd.DataFrame) -> pd.DataFrame:
    """Return positive purchases (exclude returns)."""
    return df[df["is_return"] == 0] if "is_return" in df.columns else df


def minmax(X: Any, benefit: list[bool] | None = None, eps: float = 1e-12) -> np.ndarray:
    X = np.asarray(X, float)
    m, n = X.shape
    if benefit is None:
        benefit = [True] * n
    Z = np.zeros_like(X)
    for j in range(n):
        col = X[:, j]
        rng = col.max() - col.min()
        if rng < eps:
            Z[:, j] = 0.5
        elif benefit[j]:
            Z[:, j] = (col - col.min()) / rng
        else:
            Z[:, j] = (col.max() - col) / rng
    return Z


def critic_weights(X: Any, benefit: list[bool] | None = None, eps: float = 1e-12) -> np.ndarray:
    Z = minmax(X, benefit, eps)
    n = Z.shape[1]
    std = Z.std(axis=0, ddof=1)
    corr = np.corrcoef(Z, rowvar=False) if n > 1 else np.array([[1.0]])
    corr = np.nan_to_num(corr, nan=0.0)
    C = std * np.sum(1.0 - corr, axis=1)
    return C / (C.sum() + eps)


def topsis(
    X: Any,
    weights: np.ndarray | None = None,
    benefit: list[bool] | None = None,
    eps: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray(X, float)
    if benefit is None:
        benefit = [True] * X.shape[1]
    if weights is None:
        weights = critic_weights(X, benefit, eps)
    Z = minmax(X, benefit, eps)
    V = Z * weights
    ip, ineg = V.max(axis=0), V.min(axis=0)
    Dp = np.sqrt(((V - ip) ** 2).sum(axis=1))
    Dn = np.sqrt(((V - ineg) ** 2).sum(axis=1))
    return Dn / (Dp + Dn + eps), weights


def dml_ate(
    X: Any, T: Any, Y: Any, n_folds: int = 5, discrete_treatment: bool = True
) -> tuple[float, float, tuple[float, float]]:
    """Lightweight DML: cross-fitting + Robinson partial linear."""
    from sklearn.base import clone
    from sklearn.model_selection import KFold

    try:
        from lightgbm import LGBMClassifier, LGBMRegressor

        reg = LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=30,
            verbose=-1,
            n_jobs=-1,
        )
        clf = LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=30,
            verbose=-1,
            n_jobs=-1,
        )
    except Exception:
        from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

        reg = GradientBoostingRegressor()
        clf = GradientBoostingClassifier()
    X = np.asarray(X, float)
    T = np.asarray(T, float)
    Y = np.asarray(Y, float)
    n = len(Y)
    ry = np.zeros(n)
    rt = np.zeros(n)
    kf = KFold(n_folds, shuffle=True, random_state=42)
    for tr, te in kf.split(X):
        ry[te] = Y[te] - clone(reg).fit(X[tr], Y[tr]).predict(X[te])
        if discrete_treatment:
            rt[te] = T[te] - clone(clf).fit(X[tr], T[tr].astype(int)).predict_proba(X[te])[:, 1]
        else:
            rt[te] = T[te] - clone(reg).fit(X[tr], T[tr]).predict(X[te])
    denom = np.sum(rt**2)
    theta = np.sum(rt * ry) / denom
    psi = rt * (ry - theta * rt)
    se = np.sqrt(np.mean(psi**2) / (denom / n) ** 2 / n)
    return theta, se, (theta - 1.96 * se, theta + 1.96 * se)
