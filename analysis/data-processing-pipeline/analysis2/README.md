# MarketMind 普适性分析引擎（Universal Analysis Engine）

承接 `regularization/`（数据正则化引擎）的输出，构建**只依赖标准 Schema、按 capability 自适应**的通用分析模块。任意零售数据经正则化得到标准字段 + `capability.json` 后，本引擎按能力自动运行相应分析，缺字段降级而非失败。

> 与 `regularization/` 形成闭环：**任意数据 → 正则化(标准Schema+capability) → 本引擎自适应分析**。

## 目录结构
```
analysis2/
├── config_3.py            标准数据/capability 加载、OriginLab 风格、CRITIC-TOPSIS、轻量 DML
├── analysis_engine.py     编排器：按 capability + 运行时校验自适应调度，输出跨数据集汇总
├── mod_overview.py        描述性：销售/类目帕累托/时序+季节分解/人口/促销
├── mod_profile_segment.py RFM+扩展画像 + KMeans 分群（营销区间择优）+ 雷达/散点/贡献
├── mod_association.py     FP-Growth + HUIM；运行时校验篮均，无共购则跳过
├── mod_recommendation.py  多召回(热门/类目/图嵌入SVD) + 可靠度校准融合 + 时间切分评估
├── mod_promotion.py       促销朴素对比 vs DML 去偏因果 + 折扣/利润分析
├── data/regularized/      分析输入（3 套正则化数据 dataset.csv + capability.json）
├── outputs/               分析产物（每数据集 figures/csvs + cross_dataset_summary.csv）
├── project_plan.md  report.md  00_实验汇总报告.md
```

## 用法
```bash
cd analysis2
python analysis_engine.py     # 对 data/regularized 下三组数据自适应分析
```
新数据：先用 `regularization/` 正则化，把产物放入 `data/regularized/<name>/`，在 `config_3.DATASETS` 加入名称即可。

## 5 个分析模块 ↔ 能力自适应
| 模块 | 依赖标准字段 | 运行时降级 |
|---|---|---|
| 描述性概览 | amount/cat/date/gender/promo | 按字段存在性自适应出图 |
| 画像+分群 | user_id/sale_date/amount(+可选) | 特征随字段增减；k 在营销区间择优 |
| 关联规则 | order_id + item/category | **篮均<1.5 → 跳过**（无共购结构）|
| 推荐 | user_id/item_id/amount | 复购评估用户过少 → 跳过；可靠度校准防强信号稀释 |
| 促销因果 | is_promo/amount(+混淆) | 无混淆仅朴素；有 profit 附利润分析 |

## 三组数据验证结果
| 数据集 | 分群 | 关联规则 | 促销朴素→DML | 推荐融合HitRate@10 |
|---|---|---|---|---|
| order_1 英文电商 | 3群 | **跳过**(篮均1.0) | −458→−219 | 0.039 |
| order_2 Superstore | 3群 | 1509条 | −107→+0.96(CI含0) | 0.018 |
| 销售数据 生鲜 | 4群 | 81条·薯片→膨化点心 | **+7.18→−5.18** | 0.377 |

**销售数据复现项目1核心结果**：高价值核心群贡献 58% 销售额 + 促销敏感群（促销占比0.74）；关联81条/HUIM生鲜组合；促销 DML 符号反转（朴素+7.18→去偏为负）。详见 `00_实验汇总报告.md`（含每步控制台输出）与 `report.md`。

> 推荐"热门悖论"：刚需品人人买，纯热门难超越，但融合覆盖率达其约 12 倍且具个性化，符合项目1结论。
