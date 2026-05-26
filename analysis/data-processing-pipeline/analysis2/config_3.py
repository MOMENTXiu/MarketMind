# -*- coding: utf-8 -*-
"""
项目3：普适性分析模块 · 全局配置与工具
- 读取正则化后的标准 Schema 数据 + capability
- OriginLab 风格 / 调色板 / IO
- 通用算法：标准化 / CRITIC / TOPSIS / 轻量 DML
所有分析模块只依赖【标准字段】，按 capability + 运行时校验自适应。
"""
import os
import sys
import io
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cycler

warnings.filterwarnings("ignore")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REG_DIR = os.path.join(HERE, "data", "regularized")   # 正则化产物（分析输入）
OUT_ROOT = os.path.join(HERE, "outputs")
DATASETS = ["order_1", "order_2", "销售数据"]

PALETTE = ["#2878B5", "#C82423", "#F8AC8C", "#54B345", "#9B59B6",
           "#F1B656", "#3CB1C9", "#E76254", "#7E9BB7", "#A1A9D0"]
SEQ_CMAP = "YlGnBu"
BINARY_COLORS = ("#2878B5", "#C82423")


def set_style():
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DengXian"],
        "axes.unicode_minus": False, "figure.dpi": 120, "savefig.dpi": 200,
        "savefig.bbox": "tight", "font.size": 12, "axes.linewidth": 1.1,
        "axes.edgecolor": "#333333", "axes.titlesize": 0,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.7,
        "grid.linestyle": "--", "grid.alpha": 0.6,
        "xtick.direction": "in", "ytick.direction": "in",
        "legend.frameon": False, "legend.fontsize": 9,
        "axes.prop_cycle": cycler(color=PALETTE),
    })


def _dirs(dataset):
    f = os.path.join(OUT_ROOT, dataset, "figures")
    c = os.path.join(OUT_ROOT, dataset, "csvs")
    p = os.path.join(OUT_ROOT, dataset, "pkls")
    for d in (f, c, p):
        os.makedirs(d, exist_ok=True)
    return f, c, p


def savefig(fig, dataset, name):
    for ax in fig.get_axes():
        ax.set_title("")
    f, _, _ = _dirs(dataset)
    path = os.path.join(f, name)
    fig.savefig(path); plt.close(fig)
    print(f"  [FIG] {dataset}/figures/{name}")
    return path


def save_csv(df, dataset, name, index=False):
    _, c, _ = _dirs(dataset)
    path = os.path.join(c, name)
    df.to_csv(path, index=index, encoding="utf-8-sig")
    print(f"  [CSV] {dataset}/csvs/{name}  shape={df.shape}")
    return path


def save_pkl(obj, dataset, name):
    _, _, p = _dirs(dataset)
    with open(os.path.join(p, name), "wb") as f:
        pickle.dump(obj, f)


def load_normalized(dataset):
    df = pd.read_csv(os.path.join(REG_DIR, dataset, "dataset.csv"),
                     encoding="utf-8-sig", parse_dates=["sale_date"],
                     dtype={"user_id": str, "item_id": str, "order_id": str})
    return df


def load_capability(dataset):
    with open(os.path.join(REG_DIR, dataset, "capability.json"), encoding="utf-8") as f:
        return json.load(f)


def positive(df):
    """正向购买（剔除退货）。"""
    return df[df["is_return"] == 0] if "is_return" in df.columns else df


# ---------------------------------------------------------------------------
# 通用算法
# ---------------------------------------------------------------------------
def minmax(X, benefit=None, eps=1e-12):
    X = np.asarray(X, float); m, n = X.shape
    if benefit is None:
        benefit = [True] * n
    Z = np.zeros_like(X)
    for j in range(n):
        col = X[:, j]; rng = col.max() - col.min()
        if rng < eps:
            Z[:, j] = 0.5
        elif benefit[j]:
            Z[:, j] = (col - col.min()) / rng
        else:
            Z[:, j] = (col.max() - col) / rng
    return Z


def critic_weights(X, benefit=None, eps=1e-12):
    Z = minmax(X, benefit, eps); n = Z.shape[1]
    std = Z.std(axis=0, ddof=1)
    corr = np.corrcoef(Z, rowvar=False) if n > 1 else np.array([[1.0]])
    corr = np.nan_to_num(corr, nan=0.0)
    C = std * np.sum(1.0 - corr, axis=1)
    return C / (C.sum() + eps)


def topsis(X, weights=None, benefit=None, eps=1e-12):
    X = np.asarray(X, float)
    if benefit is None:
        benefit = [True] * X.shape[1]
    if weights is None:
        weights = critic_weights(X, benefit, eps)
    Z = minmax(X, benefit, eps); V = Z * weights
    ip, ineg = V.max(axis=0), V.min(axis=0)
    Dp = np.sqrt(((V - ip) ** 2).sum(axis=1)); Dn = np.sqrt(((V - ineg) ** 2).sum(axis=1))
    return Dn / (Dp + Dn + eps), weights


def dml_ate(X, T, Y, n_folds=5, discrete_treatment=True):
    """轻量 DML（交叉拟合 + Robinson 部分线性），返回 (theta, se, ci)。"""
    from sklearn.model_selection import KFold
    from sklearn.base import clone
    try:
        from lightgbm import LGBMRegressor, LGBMClassifier
        reg = LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=31,
                            min_child_samples=30, verbose=-1, n_jobs=-1)
        clf = LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                             min_child_samples=30, verbose=-1, n_jobs=-1)
    except Exception:
        from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
        reg = GradientBoostingRegressor(); clf = GradientBoostingClassifier()
    X = np.asarray(X, float); T = np.asarray(T, float); Y = np.asarray(Y, float)
    n = len(Y); ry = np.zeros(n); rt = np.zeros(n)
    kf = KFold(n_folds, shuffle=True, random_state=42)
    for tr, te in kf.split(X):
        ry[te] = Y[te] - clone(reg).fit(X[tr], Y[tr]).predict(X[te])
        if discrete_treatment:
            rt[te] = T[te] - clone(clf).fit(X[tr], T[tr].astype(int)).predict_proba(X[te])[:, 1]
        else:
            rt[te] = T[te] - clone(reg).fit(X[tr], T[tr]).predict(X[te])
    denom = np.sum(rt ** 2)
    theta = np.sum(rt * ry) / denom
    psi = rt * (ry - theta * rt)
    se = np.sqrt(np.mean(psi ** 2) / (denom / n) ** 2 / n)
    return theta, se, (theta - 1.96 * se, theta + 1.96 * se)


if __name__ == "__main__":
    set_style()
    for ds in DATASETS:
        df = load_normalized(ds); cap = load_capability(ds)
        print(ds, df.shape, "可运行:", cap["runnable_count"])
