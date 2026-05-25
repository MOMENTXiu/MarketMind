# -*- coding: utf-8 -*-
"""
广度模块 D：顾客流失预测 + SHAP 可解释
定义：以 1–2 月为特征窗、3–4 月为标签窗。在 1–2 月活跃的顾客中，
      3–4 月无任何购买记录者记为流失(churn=1)。用 LightGBM 预测流失概率并用 SHAP 解释。

产出：
  output/csvs/churn_predictions.csv     顾客流失概率 + 高风险召回名单
  output/csvs/churn_metrics.csv          模型评估
  output/figures/ch_ROC曲线.png
  output/figures/ch_混淆矩阵.png
  output/figures/ch_SHAP重要性.png
  output/figures/ch_SHAP蜂群.png
  output/pkls/churn_model.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, roc_curve, average_precision_score,
                             confusion_matrix, classification_report)

from config import load_clean, save_csv, set_style, savefig, save_pkl, PALETTE, SEQ_CMAP

FEAT_SPLIT = pd.Timestamp("2025-03-01")   # 特征窗 < 此 ; 标签窗 >= 此
RNG = 42
EPS = 1e-9


def build_churn_dataset(df):
    pos = df[df["is_return"] == 0]
    feat = pos[pos["sale_date"] < FEAT_SPLIT]
    label = pos[pos["sale_date"] >= FEAT_SPLIT]
    Dmax = feat["sale_date"].max()
    g = feat.groupby("user_id")
    X = pd.DataFrame(index=sorted(feat["user_id"].unique()))
    X.index.name = "user_id"
    X["最近购买间隔"] = (Dmax - g["sale_date"].max()).dt.days
    X["购买频次"] = g["sale_date"].nunique()
    X["消费金额"] = g["amount"].sum()
    X["记录数"] = g.size()
    X["客单价"] = X["消费金额"] / X["购买频次"].clip(lower=1)
    X["商品数"] = g["item_id"].nunique()
    X["小类数"] = g["cat_l3_code"].nunique()
    X["促销金额占比"] = pos[pos["is_promo"] == 1].groupby("user_id")["amount"].sum().reindex(X.index).fillna(0) / X["消费金额"].clip(lower=EPS)
    X["生鲜占比"] = feat[feat["item_type"] == "生鲜"].groupby("user_id")["amount"].sum().reindex(X.index).fillna(0) / X["消费金额"].clip(lower=EPS)
    # 类目熵
    l3 = feat.pivot_table(index="user_id", columns="cat_l3_code", values="amount", aggfunc="sum", fill_value=0)
    p = l3.div(l3.sum(axis=1) + EPS, axis=0).values
    X["类目熵"] = -np.nansum(np.where(p > 0, p * np.log(p), 0), axis=1)
    # 购买活跃跨度（首末购买间隔天数）
    X["活跃跨度"] = (g["sale_date"].max() - g["sale_date"].min()).dt.days
    # 标签：标签窗是否无购买
    buyers_label = set(label["user_id"].unique())
    X["churn"] = (~X.index.isin(buyers_label)).astype(int)
    return X.reset_index()


def main():
    set_style()
    df = load_clean()
    data = build_churn_dataset(df)
    feats = ["最近购买间隔", "购买频次", "消费金额", "记录数", "客单价", "商品数",
             "小类数", "促销金额占比", "生鲜占比", "类目熵", "活跃跨度"]
    X = data[feats].values
    y = data["churn"].values
    print(f"样本 {len(data)} 人，流失率 {y.mean():.3f}")

    Xtr, Xte, ytr, yte, itr, ite = train_test_split(
        X, y, data.index.values, test_size=0.3, random_state=RNG, stratify=y)
    clf = LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31,
                         subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
                         class_weight="balanced", verbose=-1, n_jobs=-1)
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    pred = (proba >= 0.5).astype(int)
    auc = roc_auc_score(yte, proba)
    ap = average_precision_score(yte, proba)
    cm = confusion_matrix(yte, pred)
    print(f"ROC-AUC={auc:.4f}  PR-AUC={ap:.4f}")
    print(classification_report(yte, pred, target_names=["留存", "流失"]))

    met = pd.DataFrame({"指标": ["ROC-AUC", "PR-AUC", "流失率", "准确率"],
                        "数值": [round(auc, 4), round(ap, 4), round(y.mean(), 4),
                               round((pred == yte).mean(), 4)]})
    save_csv(met, "churn_metrics.csv")

    # 全量预测 + 高风险名单
    data["流失概率"] = clf.predict_proba(X)[:, 1].round(4)
    data["风险等级"] = pd.cut(data["流失概率"], [0, 0.4, 0.7, 1.0],
                          labels=["低", "中", "高"], include_lowest=True)
    out = data[["user_id", "最近购买间隔", "购买频次", "消费金额",
                "churn", "流失概率", "风险等级"]].sort_values("流失概率", ascending=False)
    save_csv(out, "churn_predictions.csv")
    n_high = (data["风险等级"] == "高").sum()
    # 高价值高风险（消费金额上40%且高风险）→ 优先召回
    hi_val = data["消费金额"].quantile(0.6)
    priority = data[(data["风险等级"] == "高") & (data["消费金额"] >= hi_val)]
    print(f"高流失风险 {n_high} 人，其中高价值优先召回 {len(priority)} 人")

    save_pkl({"model": clf, "feats": feats}, "churn_model.pkl")
    _plots(yte, proba, cm, clf, Xte, feats)
    return met, out


def _plots(yte, proba, cm, clf, Xte, feats):
    # ROC 曲线
    fpr, tpr, _ = roc_curve(yte, proba)
    auc = roc_auc_score(yte, proba)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.plot(fpr, tpr, color=PALETTE[1], lw=2.2, label=f"ROC (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], color="#999", ls="--", lw=1.2, label="随机")
    ax.set_xlabel("假阳率 FPR"); ax.set_ylabel("真阳率 TPR"); ax.legend(loc="lower right")
    savefig(fig, "ch_ROC曲线.png")

    # 混淆矩阵热力
    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(cm, cmap=SEQ_CMAP)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "#222", fontsize=14)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["预测留存", "预测流失"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["实际留存", "实际流失"])
    fig.colorbar(im, ax=ax, fraction=0.046)
    savefig(fig, "ch_混淆矩阵.png")

    # SHAP
    explainer = shap.TreeExplainer(clf)
    sv = explainer.shap_values(Xte)
    if isinstance(sv, list):
        sv = sv[1]
    Xte_df = pd.DataFrame(Xte, columns=feats)

    plt.figure(figsize=(8, 5))
    shap.summary_plot(sv, Xte_df, plot_type="bar", show=False, color=PALETTE[0])
    fig = plt.gcf()
    fig.axes[0].set_title(""); fig.axes[0].set_xlabel("平均 |SHAP 值|（特征重要性）")
    savefig(fig, "ch_SHAP重要性.png")

    plt.figure(figsize=(8, 5.5))
    shap.summary_plot(sv, Xte_df, show=False)
    fig = plt.gcf()
    fig.axes[0].set_title(""); fig.axes[0].set_xlabel("SHAP 值（对流失预测的影响）")
    if len(fig.axes) > 1:
        fig.axes[-1].set_ylabel("特征取值")
    savefig(fig, "ch_SHAP蜂群.png")


if __name__ == "__main__":
    main()
