# analysis_2 · 超市营销推荐系统（建模与因果分析）

基于超市销售明细（42,816 行 / 2,611 顾客 / 2025-01~04）的双端智能营销推荐系统：对消费者做可解释个性化推荐，对营销者做因果驱动的精准决策。

## 目录结构
```
analysis_2/
├── code_files/          # 15 个 Python 脚本 + project_plan.md
│   ├── config.py                  通用配置 / OriginLab 风格 / CRITIC-TOPSIS 工具
│   ├── causal_dml.py              双重机器学习(DML)因果工具（含自检）
│   ├── data_preprocessing.py      阶段1 数据清洗
│   ├── feature_engineering.py     阶段2 顾客/商品画像
│   ├── exp_clustering.py          阶段3 顾客分群（GMM/UMAP-HDBSCAN/AE+GMM）
│   ├── exp_association.py         阶段4 FP-Growth + 高效用项集 HUIM
│   ├── exp_recommendation.py      阶段5 多召回 + CRITIC-TOPSIS 融合
│   ├── exp_marketer.py            阶段6 营销决策 + DML 促销因果
│   ├── exp_lightgcn.py            深化 A：LightGCN 图神经推荐
│   ├── exp_uplift.py              深化 B：Uplift 发券名单（DR-learner）
│   ├── exp_churn.py               广度 D：流失预测 + SHAP
│   ├── exp_timeseries.py          广度 E：销售时序（季节分解/ACF/Holt-Winters）
│   ├── exp_clv.py                 广度 F：CLV（BG/NBD + Gamma-Gamma）
│   ├── exp_elasticity_robust.py   深化 G/C：价格弹性 + 鲁棒性检验
│   └── exp_montecarlo.py          蒙特卡洛全流程可还原性验证
├── data/                # 原始销售数据
├── docs/                # modeling_idea.md（建模思路文档 v2）
├── experimental_docs/   # 实验报告：00 总汇总 + report_01~13 + marketer_report
└── output/
    ├── figures/         # 48 张可视化（OriginLab 风格）
    ├── csvs/            # 39 个结果表（中文表头）
    └── pkls/            # 7 个模型文件
```

## 核心亮点
- **分群**：零售顾客呈双模态连续谱；AE+GMM 落地 7 营销群体，Top2 群体（46% 人）贡献 75% 销售额。
- **推荐**：图嵌入最强单召回（HitRate@10 0.443）；CRITIC-TOPSIS 融合精度持平且覆盖率最高；LightGCN 较 SVD HitRate +70%。
- **因果**：DML 揭示促销 ATE = −2.50 元/笔（纠正朴素 +7.18 的混淆），仅促销敏感群体正响应 → 精准发券（DR-learner uplift AUUC 1.70×随机）。
- **广度**：流失预测 ROC-AUC 0.78、CLV 校准相关 0.68、价格弹性 −0.25、销售时序 Holt-Winters。
- **验证**：蒙特卡洛在已知真值下还原 DML 估计偏差 <1%，方法学可信。

详见 `experimental_docs/00_实验汇总报告.md`（全量结果与控制台输出）。
