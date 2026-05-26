# -*- coding: utf-8 -*-
"""标准 Schema 定义 + 字段别名词典 + 单位/促销别名（设计报告 §6、§7、§9、§10）。"""

# ---------------------------------------------------------------------------
# 标准 Schema：字段 -> (中文名, 必需程度, 期望类型)
# 必需程度: core(强必需) / recommended(推荐) / basket / marketing
# 类型: id / date / num / cat / binary / text
# ---------------------------------------------------------------------------
STANDARD_SCHEMA = {
    "user_id":     ("顾客编号", "core", "id"),
    "sale_date":   ("销售日期", "core", "date"),
    "item_id":     ("商品编码", "core", "id"),
    "amount":      ("销售金额", "core", "num"),
    "quantity":    ("销售数量", "recommended", "num"),
    "unit_price":  ("商品单价", "recommended", "num"),
    "order_id":    ("订单号",   "basket", "id"),
    "cat_l1_name": ("大类名称", "basket", "cat"),
    "cat_l2_name": ("中类名称", "basket", "cat"),
    "cat_l3_name": ("小类名称", "basket", "cat"),
    "item_name":   ("商品名称", "basket", "text"),
    "is_promo":    ("是否促销", "marketing", "binary"),
    "discount":    ("折扣",     "marketing", "num"),
    "profit":      ("利润",     "marketing", "num"),
    "item_type":   ("商品类型", "marketing", "cat"),
    "unit":        ("单位",     "marketing", "cat"),
    "spec":        ("规格型号", "marketing", "text"),
    "store_id":    ("门店编号", "marketing", "id"),
    "region":      ("地区",     "marketing", "cat"),
    "city":        ("城市",     "marketing", "cat"),
    "segment":     ("客户细分", "marketing", "cat"),
    "gender":      ("性别",     "marketing", "cat"),
    "age":         ("年龄",     "marketing", "num"),
    "brand":       ("品牌",     "marketing", "cat"),
}

# 核心字段权重（用于字段覆盖评分 S_field）
FIELD_WEIGHTS = {
    "user_id": 3, "sale_date": 3, "item_id": 3, "amount": 3,
    "quantity": 2, "unit_price": 2, "order_id": 2,
    "cat_l1_name": 1.5, "cat_l3_name": 1.5, "item_name": 1,
    "is_promo": 1, "discount": 1, "profit": 1, "region": 0.5,
    "city": 0.5, "segment": 0.5, "gender": 0.5, "age": 0.5, "brand": 0.5,
}

# ---------------------------------------------------------------------------
# 字段别名词典（中英文，可扩展）。匹配前统一去空格/全角空格/下划线后小写。
# ---------------------------------------------------------------------------
FIELD_ALIASES = {
    "user_id":     ["顾客编号", "客户编号", "客户id", "顾客id", "会员号", "会员编号",
                    "用户编号", "用户id", "customerid", "customer_id", "userid", "user_id", "memberid"],
    "order_id":    ["订单id", "订单编号", "订单号", "小票号", "小票编号", "流水号",
                    "交易号", "交易编号", "orderid", "order_id", "billno", "bill_no", "transactionid"],
    "sale_date":   ["销售日期", "订单日期", "交易日期", "购买日期", "下单日期", "date",
                    "saledate", "sale_date", "orderdate", "order_date", "ordertime", "order_time",
                    "purchasedate", "purchase_date", "交易时间", "下单时间"],
    "item_id":     ["商品编码", "商品id", "产品id", "产品编码", "货号", "sku", "skuid",
                    "sku_id", "itemid", "item_id", "productid", "product_id"],
    "cat_l1_name": ["大类名称", "大类", "一级类目", "商品大类", "类别", "品类", "category",
                    "category_l1", "categoryl1", "maincategory"],
    "cat_l2_name": ["中类名称", "中类", "二级类目", "商品中类", "category_l2", "categoryl2"],
    "cat_l3_name": ["小类名称", "小类", "子类别", "子类目", "商品小类", "三级类目",
                    "subcategory", "sub_category", "category_l3"],
    "item_name":   ["商品名称", "产品名称", "品名", "productname", "product_name",
                    "itemname", "item_name", "goods_name"],
    "amount":      ["销售金额", "销售额", "金额", "实收金额", "成交金额", "支付金额",
                    "amount", "sales", "salesamount", "revenue", "gmv", "payamount"],
    "quantity":    ["销售数量", "数量", "销量", "件数", "购买数量", "qty", "quantity", "count", "num"],
    "unit_price":  ["商品单价", "单价", "售价", "价格", "price", "unitprice", "unit_price"],
    "is_promo":    ["是否促销", "促销", "促销标记", "活动标记", "是否活动", "promo",
                    "ispromo", "is_promo", "promotion", "promotiontype", "promotion_type"],
    "discount":    ["折扣", "折扣率", "优惠", "discount", "discountrate"],
    "profit":      ["利润", "毛利", "利润额", "profit", "margin"],
    "item_type":   ["商品类型", "产品类型", "itemtype", "item_type", "producttype"],
    "unit":        ["单位", "计量单位", "unit", "uom"],
    "spec":        ["规格型号", "规格", "型号", "spec", "specification", "model"],
    "store_id":    ["门店编号", "门店id", "店铺id", "storeid", "store_id", "shopid"],
    "region":      ["地区", "区域", "大区", "region", "area"],
    "city":        ["城市", "市", "shippingcity", "shipping_city", "city", "发货城市"],
    "segment":     ["细分", "客户细分", "用户细分", "segment", "customersegment"],
    "gender":      ["性别", "gender", "sex"],
    "age":         ["年龄", "age"],
    "brand":       ["品牌", "brand", "牌子"],
}

# 单位归一（设计报告 §10.3）
UNIT_ALIASES = {
    "千克": ["千克", "kg", "公斤", "散称", "KG", "Kg"],
    "克":   ["克", "g", "G"],
    "袋":   ["袋", "d袋"],
    "盒":   ["盒", "合"],
    "瓶":   ["瓶"], "包": ["包"], "个": ["个", "只", "支"], "件": ["件"],
    "箱":   ["箱"], "提": ["提"], "组": ["组"], "桶": ["桶"], "罐": ["罐", "听"],
}
UNIT_DIRTY = {"", "0", "2", "一般", "装", "快", "nan", "none"}

# 促销正值集合（设计报告 §9.3）
PROMO_TRUE = {"是", "y", "yes", "促销", "活动", "true", "1", "1.0", "促销品", "有"}
PROMO_FALSE = {"否", "n", "no", "非促销", "false", "0", "0.0", "none", "无", "正常", "nan", ""}
