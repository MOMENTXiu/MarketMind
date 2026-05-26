# -*- coding: utf-8 -*-
"""CapabilityChecker：分析能力判断与降级（设计报告 §12、§17.7）。
依据 normalized 数据可用的标准字段，判断各分析能力是否可运行，并记录降级原因。"""


class CapabilityChecker:
    def check(self, df):
        cols = set(df.columns)
        has = lambda *cs: all(c in cols for c in cs)

        cap = {
            "can_run_sales_stats": has("amount") or has("quantity"),
            "can_run_time_trend": has("sale_date") and (has("amount") or has("quantity")),
            "can_run_customer_profile": has("user_id") and has("amount"),
            "can_run_association": ("order_id" in cols) and (
                has("cat_l3_name") or has("cat_l2_name") or has("cat_l1_name") or has("item_id")),
            "can_run_recommendation": has("user_id", "item_id") and has("amount"),
            "can_run_forecast": has("sale_date") and has("amount"),
            "can_run_promotion_analysis": has("is_promo") and has("amount"),
            "can_run_profit_analysis": has("profit"),
            "can_run_price_sensitivity": has("unit_price") and has("amount"),
            "can_run_discount_analysis": has("discount"),
        }

        # 降级说明
        degraded = {}
        if "order_id_source" in df.columns:
            src = df["order_id_source"].iloc[0] if len(df) else None
            if src == "generated_from_user_date":
                degraded["order_id"] = "generated_from_user_date(伪订单号)"
        if "is_promo_source" in df.columns and len(df) and df["is_promo_source"].iloc[0] == "derived_from_discount":
            degraded["is_promo"] = "derived_from_discount(由折扣推导)"
        if "unit_price_source" in df.columns and len(df) and df["unit_price_source"].iloc[0] == "derived_amount_div_qty":
            degraded["unit_price"] = "derived_amount_div_qty(金额/数量推导)"
        if "profit" not in cols:
            degraded["profit"] = "missing(利润分析跳过)"
        if "is_promo" not in cols:
            degraded["is_promo"] = "missing(促销分析跳过)"

        # 中文能力摘要（供报告/前端）
        zh = {
            "基础销售统计": cap["can_run_sales_stats"],
            "时间趋势": cap["can_run_time_trend"],
            "顾客画像": cap["can_run_customer_profile"],
            "关联规则": cap["can_run_association"],
            "个性化推荐": cap["can_run_recommendation"],
            "销售预测": cap["can_run_forecast"],
            "促销分析": cap["can_run_promotion_analysis"],
            "利润分析": cap["can_run_profit_analysis"],
            "价格敏感度": cap["can_run_price_sensitivity"],
        }
        cap["degraded_fields"] = degraded
        cap["capability_zh"] = zh
        cap["runnable_count"] = sum(1 for v in zh.values() if v)
        return cap
