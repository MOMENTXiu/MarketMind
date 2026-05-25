# 超市营销推荐系统 · 项目实施方案 (project_plan.md)

> 本文件随实验迭代持续更新。最后更新：2026-05-25（初版）

---

## 0. 项目目标与双侧框架

基于 `data/销售数据.csv`（42816 条销售记录、2611 个顾客、4 个月 2025-01~2025-04）构建**双端智能营销推荐系统**：

- **消费者侧**：个性化 Top-K 商品推荐 + 推荐理由（图推荐 + 关联规则 + 类目偏好 + 复购周期 + 促销适配 → CRITIC-TOPSIS 融合排序）。
- **营销者侧**：顾客分群（UMAP+HDBSCAN / GMM）、群体价值排序、商品组合促销（FP-Growth + HUIM）、促销响应分析、品类经营建议。

技术主线（思路文档第 17 章）：
> UMAP-HDBSCAN 顾客分群 + GMM 软归属 + FP-Growth 层级关联规则 + 高效用项集挖掘(HUIM) + 图推荐召回 + CRITIC-TOPSIS 自适应排序

**增强（创新加分项）：因果推断 / 双重机器学习(DML)**
朴素 PromoLift（促销均值/非促销均值）混淆严重——被促销商品在品类、价格、顾客构成上系统性不同。引入 **Double Machine Learning（Chernozhukov 2018，交叉拟合 + Robinson 部分线性模型）** 在控制混淆变量后估计：
- 促销对销售额/数量的**去偏平均处理效应 ATE**（替代/校准 §11.3 的 PromoLift）；
- 按顾客群体的**异质处理效应 CATE**——识别促销「真正起作用」的人群，指导精准发券（uplift 思想）。
模块：`causal_dml.py`（自实现，nuisance learner 用 LightGBM/sklearn，含合成数据验证）；应用在阶段 6 营销者侧促销响应分析。

---

## 1. 数据资产与字段映射

源文件：`data/销售数据.csv`，编码 **GBK**（终端显示乱码，pandas 用 `encoding='gbk'` 正常）。

| 原字段 | 内部字段 | 类型 | 备注 |
|---|---|---|---|
| 顾客编号 | user_id | str | 2611 个，补零成定长字符串 |
| 大类编码/名称 | cat_l1_code / cat_l1_name | str | 15 大类 |
| 中类编码/名称 | cat_l2_code / cat_l2_name | str | 178 码 / 176 名 |
| 小类编码/名称 | cat_l3_code / cat_l3_name | str | 771 码 / 759 名 |
| 销售日期 | sale_date | datetime | 20250101–20250430 |
| 销售月份 | sale_month | int | 202501–202504 |
| 商品编码 | item_id | str | 6140 个 |
| 规格型号 | spec | str | 0.9% 空白→未知规格 |
| 商品类型 | item_type | cat | 一般商品/生鲜/联营商品 |
| 单位 | unit | cat | 59 种→统一映射 |
| 销售数量 | quantity | float | 允许小数（按重量） |
| 销售金额 | amount | float | |
| 商品单价 | unit_price | float | |
| 是否促销 | is_promo | int | 是→1 否→0 |

**编码-名称一致性已验证**：大/中/小类均无「一码多名」，重名是不同类目巧合同名，**一律以编码为类目主键**。

---

## 2. 数据质量诊断结论（逐列筛查）

| 问题 | 行数 | 处理 |
|---|---|---|
| 完全重复行 | 3 | 去重 |
| 错位行（规格含逗号致整体右移） | 2 (idx 8180,26902) | 还原修复 |
| 退货（销售数量<0 或金额<0） | 88 | 标记 `is_return=1`，不计入正向购买信号，保留供分析 |
| 单价=0 | 2 | 同商品→同小类中位数填补 |
| 规格型号空白 | ~380 | 填「未知规格」|
| 单位脏值/同义 | 见 §3 | 统一映射 |

**退货定义**：`quantity<=0 or amount<=0` → `is_return=1`。购物篮、关联规则、推荐训练**仅用正向购买记录**（`is_return=0`）；退货用于顾客行为分析（退货率特征）。

---

## 3. 单位统一映射表（核心预处理）

| 归一后 | 原始值 |
|---|---|
| 千克 | 千克, KG, kg, Kg, 公斤, 散称 |
| 袋 | 袋, 袋　(全角空格), d袋 |
| 盒 | 盒, 合 |
| 副 | 副, 付 |
| 代 | 代, 代　 |
| 未知单位 | (空白), 2, 0, 160g, 一般, 快, 装 等脏值 |
| 其余 | 原样保留（瓶/包/组/提/个/支/块/桶/听/杯/条/罐/只/卷/双/根/箱/板/卡/把/碗 …） |

实现：先 `strip()` 去全/半角空格，再按映射表替换，未命中且为纯数字/含字母的脏值→未知单位。

---

## 4. 代码架构

```
code_files/
├── project_plan.md              ← 本文件
├── config.py                    ← 路径/中文字体/OriginLab调色板/绘图&IO工具/CRITIC-TOPSIS工具
├── data_preprocessing.py        ← 阶段1：清洗→cleaned_sales_data.csv + 数据质量图
├── feature_engineering.py       ← 阶段2：顾客画像 + 商品画像
├── exp_clustering.py            ← 阶段3：分群实验 E1-E4
├── exp_association.py           ← 阶段4：FP-Growth + HUIM 层级关联
├── exp_recommendation.py        ← 阶段5：召回+CRITIC-TOPSIS+评估
├── exp_marketer.py              ← 阶段6：营销者侧决策
└── (project_plan.md 本文件)

experimental_docs/               ← 实验文档与策略报告
├── report_01_preprocessing.md ~ report_06_marketer.md
└── marketer_report.md           ← 营销策略报告（程序自动生成）
```

输出目录（全局约定）：
- 图：`output/figures/`（PNG，**无标题**，OriginLab 风格，中文）
- 表：`output/csvs/`（**中文表头**）
- 模型：`output/pkls/`

---

## 5. 实验路线图与进度

| 阶段 | 模块 | 产出 | 状态 |
|---|---|---|---|
| 1 | 数据预处理 | cleaned_sales_data.csv, 质量报告, 图1/2/6/7 | ✅ 完成 |
| 2 | 特征工程 | customer_profile / product_profile / repurchase_cycle, 图3/4/5/12 | ✅ 完成 |
| — | DML 因果工具 | causal_dml.py（合成数据验证通过）| ✅ 完成 |
| 3 | 顾客分群 E1-E4 | segments_*.csv（AE+GMM 7群 + HDBSCAN 2宏观）, 图8/9/10/11 | ✅ 完成 |
| 4 | 关联规则 E1-E4 | rules_item/category.csv, HUIM, 图13/14 | ✅ 完成 |
| 5 | 消费者推荐 E1-E6 | user_recommendations.csv, 评估, 图15/17/18/19 | ✅ 完成 |
| 6 | 营销者决策 | segment_value/bundle/promotion(DML)/category 策略, marketer_report.md, 图16 | ✅ 完成 |

### 拓展与深化模块（v2，报告见 experimental_docs/report_07~13）
| 模块 | 脚本 | 产出/结论 |
|---|---|---|
| A LightGCN | `exp_lightgcn.py` | HitRate@10 0.351 vs SVD 0.206（+70%）|
| B Uplift 发券 | `exp_uplift.py` | DR-learner，AUUC 1.70×随机；发券名单 1046 人 |
| D 流失预测 | `exp_churn.py` | ROC-AUC 0.78 + SHAP；优先召回 218 人 |
| E 销售时序 | `exp_timeseries.py` | 季节分解+ACF/PACF+Holt-Winters，RMSE 优于朴素 13.7% |
| F CLV | `exp_clv.py` | BG/NBD+Gamma-Gamma，校准相关 0.68；Top10% 占 56.9% |
| G/C 弹性+鲁棒 | `exp_elasticity_robust.py` | 弹性 −0.25；规则 36/43 显著；聚类 ARI 0.48 |
| MC 蒙特卡洛验证 | `exp_montecarlo.py` | 合成已知真值，检验全流程可还原性 |

### 关键结论速览
- **分群**：零售顾客本质是双模态连续谱；AE+GMM(7群) 指标优于裸 GMM，Top2 群体（46%人）贡献 75% 销售额。
- **关联**：小类级 73 规则；HUIM 捕获「根茎+鲜猪肉」等低频高价值组合（篮均效用 22.4 元）。
- **推荐**：图嵌入是最强单召回(HitRate 0.443)；CRITIC-TOPSIS 融合精度持平且覆盖率达其 1.4 倍、全面可解释。
- **因果**：DML 揭示促销 ATE = −2.50 元/笔（朴素 +7.18 的符号被纠正）；仅「促销敏感型2」正响应 → 精准促销而非全员撒券。

---

## 6. 评估与验收标准

- **分群**：Silhouette / Davies-Bouldin / Calinski-Harabasz + 群体销售贡献差异 + 营销解释性。
- **关联规则**：规则数、平均 confidence/lift、高效用组合数、可解释占比。
- **推荐**：时间切分（前 3 个月训练 / 第 4 个月验证）→ Precision@K / Recall@K / HitRate@K / NDCG@K / Coverage / Diversity / PromoMatchRate；CRITIC-TOPSIS 融合需优于单一召回。
- **营销策略**：覆盖人数、促销响应率、高价值顾客覆盖率。

每阶段结果须自评估、迭代至「可接受的优秀表现且能通过检验」方进入下一步。

---

## 7. 绘图与输出规范

- 无 title；中文标签（SimHei/Microsoft YaHei）；OriginLab 风格（白底、细边框、tick 内向、无顶右脊）。
- 自定义调色板，避免单一图型过多，按思路文档第 15 章图表清单覆盖数据探索/模型诊断/分组/时序/对比五类。
- 表格中文表头，UTF-8-SIG 保存便于 Excel 打开。
