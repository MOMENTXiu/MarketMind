# MarketMind 普适性分析模块 · 实施方案（project_plan_3.md）

> 配合正则化引擎（code_files_2），构建**只依赖标准 Schema、按 capability 自适应**的分析模块。
> 借鉴 code_files（项目1·销售数据）的分析思路，但不绑定固定中文字段；方法可调整，以"每步结果可接受"为准，尤其保证 `销售数据` 不逊于项目1。

## 0. 设计原则
1. **标准字段驱动**：所有模块只读正则化输出的标准字段（user_id/sale_date/item_id/amount/quantity/unit_price/order_id/cat_l*_name/is_promo/discount/profit/...），不硬编码任意数据集的原始列名。
2. **能力自适应 + 运行时校验**：读取 `capability.json` 决定运行哪些模块；模块内再做运行时可行性校验（如关联规则需多品篮），缺字段降级而非失败。
3. **结果可接受优先**：算法按数据特性择优（如分群在营销区间 [3,6] 选 k；推荐用可靠度校准融合）。

## 1. 代码架构（`code_files_3/`）
```
config_3.py            标准Schema加载/capability/OriginLab风格/CRITIC-TOPSIS/轻量DML
analysis_engine.py     编排器：按 capability+运行时校验自适应调度，输出跨数据集汇总
mod_overview.py        描述性：销售/类目帕累托/时序+季节分解/人口/促销（自适应字段）
mod_profile_segment.py RFM+扩展画像 + KMeans 分群（[3,6]区间择优）+ 雷达/散点/贡献
mod_association.py     FP-Growth 关联规则 + HUIM；运行时校验篮均，无共购则跳过
mod_recommendation.py  多召回(热门/类目/图嵌入SVD) + 可靠度校准的加权融合 + 时间切分评估
mod_promotion.py       促销朴素对比 vs DML去偏因果 + 折扣/利润分析
```
输出：`output_3/{数据集}/{figures,csvs,pkls}` + `output_3/cross_dataset_summary.csv`。

## 2. 模块 ↔ capability ↔ 运行时校验
| 模块 | capability 键 | 运行时校验/降级 |
|---|---|---|
| 描述性概览 | can_run_sales_stats | 按 amount/cat/date/gender/promo 存在性自适应出图 |
| 画像+分群 | can_run_customer_profile | 特征随字段增减；k 在 [3,6] 择优（小数据退化到[2,3]）|
| 关联规则 | can_run_association | **篮均<1.5 或多品篮<10% → 跳过**（如 order_1）|
| 推荐 | can_run_recommendation | 复购评估用户<10 → 跳过；可靠度校准防强信号被稀释 |
| 促销因果 | can_run_promotion_analysis | 无混淆变量时仅朴素对比；有 profit 则附利润分析 |

## 3. 三组验证数据（正则化后）
| 数据集 | 来源 | 行/用户/订单 | 篮均 | 复购 | 特性 |
|---|---|---|---|---|---|
| order_1 | 英文电商 | 1693/1468/1693 | 1.00 | 13% | 单品订单、有人口属性 |
| order_2 | Superstore | 9959/790/2770 | 3.60 | 99% | 4年跨度、有利润/折扣/地区 |
| 销售数据 | 生鲜超市 | 42813/2611/8942 | 4.79 | 94% | 项目1基准，三级类目 |

## 4. 验收标准
- 每模块对三组数据均「正确运行或合理降级」，无崩溃；
- `销售数据` 关联规则/HUIM、促销 DML、分群画像达到项目1水准；
- 跨数据集汇总可解释；结果写入报告并自评估。

## 5. 状态：✅ 已完成并通过三组数据验证（详见 report_analysis.md）
