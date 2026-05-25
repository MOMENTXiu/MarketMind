# -*- coding: utf-8 -*-
"""
双重机器学习（Double Machine Learning, DML）因果推断工具
参考 Chernozhukov et al. (2018) Double/Debiased Machine Learning。

部分线性模型：  Y = θ·T + g(X) + ε ,   T = m(X) + ν
交叉拟合(cross-fitting) 估计 nuisance：
    ĝ(X)=E[Y|X],  m̂(X)=E[T|X]   （out-of-fold 预测，消除过拟合偏差）
残差正交化(Robinson)：
    Ỹ = Y − ĝ(X) ,  T̃ = T − m̂(X)
ATE 估计：  θ̂ = (Σ T̃ Ỹ)/(Σ T̃²)
渐近方差(影响函数)：  Var(θ̂) = E[ψ²]/(n·E[T̃²]²),  ψ = T̃(Ỹ − θ̂ T̃)

异质效应 CATE：在残差空间对子群分别估计 θ̂_g，或用线性最终阶段 Ỹ = Σ_k β_k (T̃·X_k)。

本实现自包含（nuisance learner 用 sklearn/LightGBM），不依赖 econml/dowhy。
"""
import sys
import io
import warnings
import numpy as np
from sklearn.model_selection import KFold
from sklearn.base import clone

warnings.filterwarnings("ignore")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

try:
    from lightgbm import LGBMRegressor, LGBMClassifier
    _HAS_LGBM = True
except Exception:
    _HAS_LGBM = False
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier


def _default_reg():
    if _HAS_LGBM:
        return LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31,
                             subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
                             verbose=-1, n_jobs=-1)
    return GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3)


def _default_clf():
    if _HAS_LGBM:
        return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                              subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
                              verbose=-1, n_jobs=-1)
    return GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=3)


def dml_partial_linear(X, T, Y, n_folds=5, model_y=None, model_t=None,
                       discrete_treatment=True, random_state=42):
    """部分线性 DML，估计标量处理效应 θ（ATE）。

    Parameters
    ----------
    X : (n,p) 混淆变量
    T : (n,)  处理变量（discrete_treatment=True 时按二分类建模倾向）
    Y : (n,)  结果变量
    返回 dict: theta, se, ci95, t_stat, pval, resid_t, resid_y
    """
    X = np.asarray(X, float)
    T = np.asarray(T, float)
    Y = np.asarray(Y, float)
    n = len(Y)
    model_y = model_y or _default_reg()
    model_t = model_t or (_default_clf() if discrete_treatment else _default_reg())

    res_y = np.zeros(n)
    res_t = np.zeros(n)
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    for tr, te in kf.split(X):
        my = clone(model_y).fit(X[tr], Y[tr])
        res_y[te] = Y[te] - my.predict(X[te])
        mt = clone(model_t)
        if discrete_treatment:
            mt.fit(X[tr], T[tr].astype(int))
            res_t[te] = T[te] - mt.predict_proba(X[te])[:, 1]
        else:
            mt.fit(X[tr], T[tr])
            res_t[te] = T[te] - mt.predict(X[te])

    denom = np.sum(res_t ** 2)
    theta = np.sum(res_t * res_y) / denom
    psi = res_t * (res_y - theta * res_t)
    var = np.mean(psi ** 2) / (denom / n) ** 2 / n
    se = np.sqrt(var)
    from scipy import stats
    t_stat = theta / se
    pval = 2 * (1 - stats.norm.cdf(abs(t_stat)))
    return {"theta": theta, "se": se, "t_stat": t_stat, "pval": pval,
            "ci95": (theta - 1.96 * se, theta + 1.96 * se),
            "resid_t": res_t, "resid_y": res_y, "n": n}


def dml_group_cate(X, T, Y, groups, **kwargs):
    """按离散分组估计异质处理效应 CATE：先全样本交叉拟合得到残差，
    再在每个组内用 Robinson 估计 θ_g（共享 nuisance，组间可比）。
    返回 {group: {theta, se, ci95, n}}。
    """
    base = dml_partial_linear(X, T, Y, **kwargs)
    rt, ry = base["resid_t"], base["resid_y"]
    groups = np.asarray(groups)
    out = {"_overall": {"theta": base["theta"], "se": base["se"],
                        "ci95": base["ci95"], "n": base["n"]}}
    for g in sorted(set(groups.tolist())):
        m = groups == g
        if m.sum() < 30:
            continue
        denom = np.sum(rt[m] ** 2)
        if denom < 1e-9:
            continue
        th = np.sum(rt[m] * ry[m]) / denom
        psi = rt[m] * (ry[m] - th * rt[m])
        var = np.mean(psi ** 2) / (denom / m.sum()) ** 2 / m.sum()
        se = np.sqrt(var)
        out[str(g)] = {"theta": th, "se": se,
                       "ci95": (th - 1.96 * se, th + 1.96 * se), "n": int(m.sum())}
    return out


def naive_diff(T, Y):
    """朴素均值差（混淆，作为对照基线）。"""
    T = np.asarray(T); Y = np.asarray(Y)
    return Y[T == 1].mean() - Y[T == 0].mean()


# ---------------------------------------------------------------------------
# 合成数据自检：验证 DML 能还原已知因果效应、且优于朴素均值差
# ---------------------------------------------------------------------------
def _self_test():
    rng = np.random.default_rng(0)
    n, p = 4000, 8
    X = rng.normal(size=(n, p))
    # 混淆：倾向 T 依赖 X；结果 Y 也依赖 X（非线性）→ 朴素差有偏
    logit = 0.8 * X[:, 0] - 0.6 * X[:, 1] + 0.4 * X[:, 2]
    pT = 1 / (1 + np.exp(-logit))
    T = (rng.uniform(size=n) < pT).astype(int)
    true_theta = 2.0
    gX = 1.5 * np.sin(X[:, 0]) + X[:, 1] ** 2 - 0.5 * X[:, 2] * X[:, 3]
    Y = true_theta * T + gX + rng.normal(scale=1.0, size=n)

    naive = naive_diff(T, Y)
    res = dml_partial_linear(X, T, Y, n_folds=5)
    print("=== DML 合成数据自检 ===")
    print(f"真实因果效应 θ = {true_theta}")
    print(f"朴素均值差(有偏)  = {naive:.4f}   偏差 {naive-true_theta:+.4f}")
    print(f"DML 估计 theta_hat = {res['theta']:.4f}  (SE={res['se']:.4f}, "
          f"95%CI=[{res['ci95'][0]:.3f},{res['ci95'][1]:.3f}], p={res['pval']:.1e})")
    ok = abs(res["theta"] - true_theta) < 0.15 and abs(res["theta"] - true_theta) < abs(naive - true_theta)
    print("结果:", "通过 ✅ DML 显著优于朴素差且接近真值" if ok else "未通过 ❌")
    return ok


if __name__ == "__main__":
    _self_test()
