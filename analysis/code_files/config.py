# -*- coding: utf-8 -*-
"""
全局配置与工具库
- 路径管理 / 中文字体 / OriginLab 风格 / 调色板
- IO 工具（中文表头 CSV、pkl）
- 通用算法工具：标准化、CRITIC 权重、TOPSIS 排序、熵权法
所有实验脚本统一 `from config import *` 或按需导入。
"""
import os
import sys
import io
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cycler

# 让 print 中文在 Windows 终端正常
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

# ----------------------------------------------------------------------------
# 路径
# ----------------------------------------------------------------------------
ROOT = r"D:\new_Marketmind"
DATA_FILE = os.path.join(ROOT, "data", "销售数据.csv")
CODE_DIR = os.path.join(ROOT, "code_files")
DOCS_DIR = os.path.join(ROOT, "experimental_docs")   # 实验文档/策略报告
OUT_DIR = os.path.join(ROOT, "output")
FIG_DIR = os.path.join(OUT_DIR, "figures")
CSV_DIR = os.path.join(OUT_DIR, "csvs")
PKL_DIR = os.path.join(OUT_DIR, "pkls")
for _d in (FIG_DIR, CSV_DIR, PKL_DIR, DOCS_DIR):
    os.makedirs(_d, exist_ok=True)

CLEAN_FILE = os.path.join(CSV_DIR, "cleaned_sales_data.csv")

DATA_ENCODING = "gbk"

# ----------------------------------------------------------------------------
# OriginLab 风格调色板（高区分度、印刷友好）
# ----------------------------------------------------------------------------
# 主序列调色板
PALETTE = [
    "#2878B5", "#C82423", "#F8AC8C", "#54B345", "#9B59B6",
    "#F1B656", "#3CB1C9", "#E76254", "#7E9BB7", "#A1A9D0",
]
# 顺序型（热力/密度）
SEQ_CMAP = "YlGnBu"
DIVERGE_CMAP = "RdBu_r"
# 双色（促销/非促销 等二分对比）
BINARY_COLORS = ("#2878B5", "#C82423")


def set_style():
    """设置 OriginLab 风格 + 中文字体。每个绘图脚本开头调用一次。"""
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DengXian"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.size": 12,
        "axes.linewidth": 1.1,
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#222222",
        "axes.titlesize": 0,            # 禁用 title
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#DDDDDD",
        "grid.linewidth": 0.7,
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "axes.prop_cycle": cycler(color=PALETTE),
    })


def savefig(fig, name):
    """保存图到 output/figures，强制无 title。"""
    for ax in fig.get_axes():
        ax.set_title("")
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"[FIG] {path}")
    return path


def save_csv(df, name, index=False):
    """保存中文表头 CSV（utf-8-sig 便于 Excel）。"""
    path = os.path.join(CSV_DIR, name)
    df.to_csv(path, index=index, encoding="utf-8-sig")
    print(f"[CSV] {path}  shape={df.shape}")
    return path


def save_pkl(obj, name):
    path = os.path.join(PKL_DIR, name)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"[PKL] {path}")
    return path


def load_pkl(name):
    with open(os.path.join(PKL_DIR, name), "rb") as f:
        return pickle.load(f)


def load_clean():
    """载入清洗后的数据，恢复 dtype。"""
    df = pd.read_csv(CLEAN_FILE, encoding="utf-8-sig", dtype={
        "user_id": str, "item_id": str,
        "cat_l1_code": str, "cat_l2_code": str, "cat_l3_code": str,
    })
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


# ----------------------------------------------------------------------------
# 通用算法工具：标准化 / CRITIC / TOPSIS / 熵权
# ----------------------------------------------------------------------------
def minmax_normalize(X, benefit=None, eps=1e-12):
    """Min-Max 标准化到 [0,1]。
    X: (m,n) ndarray；benefit: 长度 n 的 bool 列表，True=正向(越大越好)，False=负向。
    """
    X = np.asarray(X, dtype=float)
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


def critic_weights(X, benefit=None, eps=1e-12):
    """CRITIC 权重法。先 min-max 标准化（考虑方向），再 C_j = sigma_j * sum_k(1-r_jk)。
    返回 (weights[n], info{std, conflict, C})。
    """
    Z = minmax_normalize(X, benefit, eps)
    n = Z.shape[1]
    std = Z.std(axis=0, ddof=1)
    if n == 1:
        corr = np.array([[1.0]])
    else:
        corr = np.corrcoef(Z, rowvar=False)
        corr = np.nan_to_num(corr, nan=0.0)
    conflict = np.sum(1.0 - corr, axis=1)        # 每个指标与其他指标的冲突性
    C = std * conflict
    w = C / (C.sum() + eps)
    info = {"std": std, "conflict": conflict, "C": C}
    return w, info


def entropy_weights(X, benefit=None, eps=1e-12):
    """熵权法权重。返回 weights[n]。"""
    Z = minmax_normalize(X, benefit, eps) + eps
    P = Z / Z.sum(axis=0, keepdims=True)
    m = Z.shape[0]
    k = 1.0 / np.log(m)
    E = -k * np.sum(P * np.log(P), axis=0)
    d = 1.0 - E
    w = d / (d.sum() + eps)
    return w


def topsis(X, weights=None, benefit=None, eps=1e-12):
    """TOPSIS 综合排序。
    X:(m,n)；weights 缺省用 CRITIC 自动计算。
    返回 (closeness[m], detail{Dp, Dn, weights, ideal_pos, ideal_neg})。
    """
    X = np.asarray(X, dtype=float)
    if benefit is None:
        benefit = [True] * X.shape[1]
    if weights is None:
        weights, _ = critic_weights(X, benefit, eps)
    Z = minmax_normalize(X, benefit, eps)         # 方向已在此统一为「越大越好」
    V = Z * weights
    ideal_pos = V.max(axis=0)
    ideal_neg = V.min(axis=0)
    Dp = np.sqrt(((V - ideal_pos) ** 2).sum(axis=1))
    Dn = np.sqrt(((V - ideal_neg) ** 2).sum(axis=1))
    closeness = Dn / (Dp + Dn + eps)
    return closeness, {"Dp": Dp, "Dn": Dn, "weights": weights,
                       "ideal_pos": ideal_pos, "ideal_neg": ideal_neg}


if __name__ == "__main__":
    set_style()
    print("ROOT:", ROOT)
    print("字体/风格已就绪。调色板色数:", len(PALETTE))
    # 自检 CRITIC-TOPSIS
    Xtest = np.array([[8, 7, 2], [5, 9, 4], [9, 6, 3], [6, 8, 5]], float)
    w, info = critic_weights(Xtest)
    c, _ = topsis(Xtest, w)
    print("CRITIC 权重:", np.round(w, 4), "TOPSIS 贴近度:", np.round(c, 4))
