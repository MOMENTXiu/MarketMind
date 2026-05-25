"""
销售预测服务 - 基于Ridge回归的时间序列预测
"""

from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler


class PredictionService:
    """销售额和利润预测服务类"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.sales_model = None
        self.profit_model = None
        self.scaler_sales_X = StandardScaler()
        self.scaler_sales_y = StandardScaler()
        self.scaler_profit_X = StandardScaler()
        self.scaler_profit_y = StandardScaler()

    async def analyze(self, forecast_weeks: int = 13) -> Dict[str, Any]:
        """
        执行销售预测分析

        Args:
            forecast_weeks: 预测未来周数

        Returns:
            预测结果字典
        """
        try:
            # 1. 加载数据
            df = pd.read_csv(self.data_path, encoding="utf-8")
            df["订单日期"] = pd.to_datetime(df["订单日期"])

            # 2. 构建周度数据
            weekly_sales = self._build_weekly_data(df)

            # 3. 特征工程
            weekly_sales = self._feature_engineering(weekly_sales)

            # 4. 准备训练数据
            train_data = weekly_sales.dropna().reset_index(drop=True)

            # 5. 训练模型
            sales_r2, profit_r2 = self._train_models(train_data)

            # 6. 生成预测
            forecast_results, summary = self._generate_forecast(
                weekly_sales, train_data, forecast_weeks
            )

            return {
                "success": True,
                "message": "销售预测完成",
                "data": {
                    "sales_r2": round(sales_r2, 4),
                    "profit_r2": round(profit_r2, 4),
                    "train_samples": len(train_data),
                    "forecast_weeks": forecast_weeks,
                    "forecast_data": forecast_results,
                    "forecast_summary": summary,
                },
            }

        except Exception as e:
            return {"success": False, "message": f"预测失败: {str(e)}", "data": {}}

    def _build_weekly_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """构建周度聚合数据"""
        df["年周"] = df["订单日期"].dt.strftime("%Y-%W")

        weekly_sales = (
            df.groupby("年周")
            .agg(
                {
                    "销售额": "sum",
                    "利润": "sum",
                    "订单 ID": "nunique",
                    "数量": "sum",
                    "订单日期": "min",
                }
            )
            .reset_index()
        )

        weekly_sales.columns = ["年周", "销售额", "利润", "订单数", "销量", "日期"]
        weekly_sales = weekly_sales.sort_values("日期").reset_index(drop=True)

        # 去除异常值
        weekly_sales = self._remove_outliers(weekly_sales, "销售额", factor=2.0)
        weekly_sales = weekly_sales.reset_index(drop=True)

        return weekly_sales

    def _remove_outliers(
        self, data: pd.DataFrame, column: str, factor: float = 1.5
    ) -> pd.DataFrame:
        """使用IQR方法去除异常值"""
        Q1 = data[column].quantile(0.25)
        Q3 = data[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - factor * IQR
        upper = Q3 + factor * IQR
        return data[(data[column] >= lower) & (data[column] <= upper)]

    def _feature_engineering(self, weekly_sales: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        # 时间特征
        weekly_sales["周序号"] = range(len(weekly_sales))
        weekly_sales["月份"] = weekly_sales["日期"].dt.month
        weekly_sales["季度"] = weekly_sales["日期"].dt.quarter
        weekly_sales["是否月初"] = (weekly_sales["日期"].dt.day <= 7).astype(int)
        weekly_sales["是否月末"] = (weekly_sales["日期"].dt.day >= 24).astype(int)

        # 周期性编码
        weekly_sales["月份_sin"] = np.sin(2 * np.pi * weekly_sales["月份"] / 12)
        weekly_sales["月份_cos"] = np.cos(2 * np.pi * weekly_sales["月份"] / 12)
        weekly_sales["季度_sin"] = np.sin(2 * np.pi * weekly_sales["季度"] / 4)
        weekly_sales["季度_cos"] = np.cos(2 * np.pi * weekly_sales["季度"] / 4)

        # 滞后特征
        for lag in [1, 2, 3, 4]:
            weekly_sales[f"销售额_lag{lag}"] = weekly_sales["销售额"].shift(lag)
            weekly_sales[f"利润_lag{lag}"] = weekly_sales["利润"].shift(lag)

        # 滑动窗口特征
        for window in [3, 4, 6]:
            weekly_sales[f"销售额_ma{window}"] = (
                weekly_sales["销售额"].rolling(window=window, min_periods=1).mean()
            )
            weekly_sales[f"销售额_std{window}"] = (
                weekly_sales["销售额"].rolling(window=window, min_periods=1).std().fillna(0)
            )
            weekly_sales[f"利润_ma{window}"] = (
                weekly_sales["利润"].rolling(window=window, min_periods=1).mean()
            )
            weekly_sales[f"利润_std{window}"] = (
                weekly_sales["利润"].rolling(window=window, min_periods=1).std().fillna(0)
            )

        # 趋势特征
        weekly_sales["销售额_diff"] = weekly_sales["销售额"].diff().fillna(0)
        weekly_sales["利润_diff"] = weekly_sales["利润"].diff().fillna(0)
        weekly_sales["销售额_pct"] = weekly_sales["销售额"].pct_change().fillna(0).clip(-1, 1)
        weekly_sales["利润_pct"] = weekly_sales["利润"].pct_change().fillna(0).clip(-1, 1)

        return weekly_sales

    def _train_models(self, train_data: pd.DataFrame) -> tuple:
        """训练销售额和利润预测模型"""
        # 销售额特征
        sales_feature_cols = [
            "周序号",
            "月份_sin",
            "月份_cos",
            "季度_sin",
            "季度_cos",
            "是否月初",
            "是否月末",
            "销售额_lag1",
            "销售额_lag2",
            "销售额_lag3",
            "销售额_lag4",
            "销售额_ma3",
            "销售额_ma4",
            "销售额_ma6",
            "销售额_std3",
            "销售额_diff",
            "销售额_pct",
        ]

        # 利润特征
        profit_feature_cols = [
            "周序号",
            "月份_sin",
            "月份_cos",
            "季度_sin",
            "季度_cos",
            "是否月初",
            "是否月末",
            "利润_lag1",
            "利润_lag2",
            "利润_lag3",
            "利润_lag4",
            "利润_ma3",
            "利润_ma4",
            "利润_ma6",
            "利润_std3",
            "利润_diff",
            "利润_pct",
            "销售额_lag1",
        ]

        # 准备数据
        X_sales = train_data[sales_feature_cols].values
        y_sales = train_data["销售额"].values
        X_profit = train_data[profit_feature_cols].values
        y_profit = train_data["利润"].values

        # 标准化
        X_sales_scaled = self.scaler_sales_X.fit_transform(X_sales)
        y_sales_scaled = self.scaler_sales_y.fit_transform(y_sales.reshape(-1, 1)).ravel()
        X_profit_scaled = self.scaler_profit_X.fit_transform(X_profit)
        y_profit_scaled = self.scaler_profit_y.fit_transform(y_profit.reshape(-1, 1)).ravel()

        # 训练模型
        self.sales_model = Ridge(alpha=10.0)
        self.profit_model = Ridge(alpha=10.0)

        self.sales_model.fit(X_sales_scaled, y_sales_scaled)
        self.profit_model.fit(X_profit_scaled, y_profit_scaled)

        # 评估模型
        sales_pred_scaled = self.sales_model.predict(X_sales_scaled)
        profit_pred_scaled = self.profit_model.predict(X_profit_scaled)

        sales_r2 = r2_score(y_sales_scaled, sales_pred_scaled)
        profit_r2 = r2_score(y_profit_scaled, profit_pred_scaled)

        return sales_r2, profit_r2

    def _generate_forecast(
        self, weekly_sales: pd.DataFrame, train_data: pd.DataFrame, forecast_weeks: int
    ) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
        """基于最近周度数据进行多步预测"""
        forecast_results: list[Dict[str, Any]] = []

        # 使用最近的真实周度数据作为起点
        last_week = train_data.iloc[-1]
        last_date = weekly_sales["日期"].max()

        # 历史序列，用于滚动更新特征
        sales_history = list(train_data["销售额"].values)
        profit_history = list(train_data["利润"].values)

        # 预测所需的特征字段
        def build_features(future_date, future_week_idx):
            month = future_date.month
            quarter = (month - 1) // 3 + 1
            is_month_start = int(future_date.day <= 7)
            is_month_end = int(future_date.day >= 24)

            def lag(series, k, default=0.0):
                return series[-k] if len(series) >= k else default

            def ma(series, window):
                if len(series) == 0:
                    return 0.0
                return float(np.mean(series[-window:]))

            def std(series, window):
                if len(series) == 0:
                    return 0.0
                return float(np.std(series[-window:]))

            def diff(series):
                return series[-1] - series[-2] if len(series) >= 2 else 0.0

            def pct(series):
                if len(series) >= 2 and series[-2] != 0:
                    return float(np.clip((series[-1] - series[-2]) / series[-2], -1, 1))
                return 0.0

            # 销售额特征
            sales_feats = [
                future_week_idx,
                np.sin(2 * np.pi * month / 12),
                np.cos(2 * np.pi * month / 12),
                np.sin(2 * np.pi * quarter / 4),
                np.cos(2 * np.pi * quarter / 4),
                is_month_start,
                is_month_end,
                lag(sales_history, 1),
                lag(sales_history, 2),
                lag(sales_history, 3),
                lag(sales_history, 4),
                ma(sales_history, 3),
                ma(sales_history, 4),
                ma(sales_history, 6),
                std(sales_history, 3),
                diff(sales_history),
                pct(sales_history),
            ]

            # 利润特征
            profit_feats = [
                future_week_idx,
                np.sin(2 * np.pi * month / 12),
                np.cos(2 * np.pi * month / 12),
                np.sin(2 * np.pi * quarter / 4),
                np.cos(2 * np.pi * quarter / 4),
                is_month_start,
                is_month_end,
                lag(profit_history, 1),
                lag(profit_history, 2),
                lag(profit_history, 3),
                lag(profit_history, 4),
                ma(profit_history, 3),
                ma(profit_history, 4),
                ma(profit_history, 6),
                std(profit_history, 3),
                diff(profit_history),
                pct(profit_history),
                lag(sales_history, 1),
            ]

            return sales_feats, profit_feats

        # 迭代多步预测，使用前一步预测值更新序列
        for i in range(1, forecast_weeks + 1):
            future_date = last_date + pd.Timedelta(weeks=i)
            future_week_idx = int(last_week["周序号"] + i)

            sales_feats, profit_feats = build_features(future_date, future_week_idx)

            X_sales_scaled = self.scaler_sales_X.transform([sales_feats])
            X_profit_scaled = self.scaler_profit_X.transform([profit_feats])

            sales_pred_scaled = self.sales_model.predict(X_sales_scaled)
            profit_pred_scaled = self.profit_model.predict(X_profit_scaled)

            sales_pred = float(
                self.scaler_sales_y.inverse_transform(sales_pred_scaled.reshape(-1, 1))[0][0]
            )
            profit_pred = float(
                self.scaler_profit_y.inverse_transform(profit_pred_scaled.reshape(-1, 1))[0][0]
            )

            sales_history.append(sales_pred)
            profit_history.append(profit_pred)

            profit_rate = (profit_pred / sales_pred * 100) if sales_pred != 0 else 0.0

            forecast_results.append(
                {
                    "week": i,
                    "date": future_date.strftime("%Y-%m-%d"),
                    "sales": round(sales_pred, 2),
                    "profit": round(profit_pred, 2),
                    "profit_rate": round(profit_rate, 2),
                }
            )

        total_sales = sum(item["sales"] for item in forecast_results)
        total_profit = sum(item["profit"] for item in forecast_results)
        avg_profit_rate = (total_profit / total_sales * 100) if total_sales != 0 else 0.0

        summary = {
            "total_sales": round(total_sales, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit_rate": round(avg_profit_rate, 2),
        }

        return forecast_results, summary
