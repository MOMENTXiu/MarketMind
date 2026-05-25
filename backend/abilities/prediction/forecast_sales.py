"""Sales forecast ability."""

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler


def forecast_sales(dataset: pd.DataFrame, forecast_weeks: int = 13) -> dict[str, Any]:
    """Forecast weekly sales and profit from an explicit dataset."""

    try:
        weekly_sales = _build_weekly_data(dataset.copy())
        weekly_sales = _feature_engineering(weekly_sales)
        train_data = weekly_sales.dropna().reset_index(drop=True)
        if len(train_data) < 2:
            raise ValueError("训练数据不足，无法进行预测")

        model_state = _train_models(train_data)
        forecast_data, summary = _generate_forecast(
            weekly_sales,
            train_data,
            forecast_weeks,
            model_state,
        )

        return {
            "success": True,
            "message": "销售预测完成",
            "data": {
                "sales_r2": round(model_state["sales_r2"], 4),
                "profit_r2": round(model_state["profit_r2"], 4),
                "train_samples": len(train_data),
                "forecast_weeks": forecast_weeks,
                "forecast_data": forecast_data,
                "forecast_summary": summary,
            },
        }
    except Exception as exc:
        return {"success": False, "message": f"预测失败: {exc}", "data": {}}


def _build_weekly_data(dataset: pd.DataFrame) -> pd.DataFrame:
    dataset["订单日期"] = pd.to_datetime(dataset["订单日期"])
    dataset["年周"] = dataset["订单日期"].dt.strftime("%Y-%W")
    weekly_sales = (
        dataset.groupby("年周")
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
    return _remove_outliers(weekly_sales, "销售额", factor=2.0).reset_index(drop=True)


def _remove_outliers(data: pd.DataFrame, column: str, factor: float) -> pd.DataFrame:
    q1 = data[column].quantile(0.25)
    q3 = data[column].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    return data[(data[column] >= lower) & (data[column] <= upper)]


def _feature_engineering(weekly_sales: pd.DataFrame) -> pd.DataFrame:
    weekly_sales["周序号"] = range(len(weekly_sales))
    weekly_sales["月份"] = weekly_sales["日期"].dt.month
    weekly_sales["季度"] = weekly_sales["日期"].dt.quarter
    weekly_sales["是否月初"] = (weekly_sales["日期"].dt.day <= 7).astype(int)
    weekly_sales["是否月末"] = (weekly_sales["日期"].dt.day >= 24).astype(int)
    weekly_sales["月份_sin"] = np.sin(2 * np.pi * weekly_sales["月份"] / 12)
    weekly_sales["月份_cos"] = np.cos(2 * np.pi * weekly_sales["月份"] / 12)
    weekly_sales["季度_sin"] = np.sin(2 * np.pi * weekly_sales["季度"] / 4)
    weekly_sales["季度_cos"] = np.cos(2 * np.pi * weekly_sales["季度"] / 4)

    for lag in [1, 2, 3, 4]:
        weekly_sales[f"销售额_lag{lag}"] = weekly_sales["销售额"].shift(lag)
        weekly_sales[f"利润_lag{lag}"] = weekly_sales["利润"].shift(lag)
    for window in [3, 4, 6]:
        weekly_sales[f"销售额_ma{window}"] = (
            weekly_sales["销售额"].rolling(window, min_periods=1).mean()
        )
        weekly_sales[f"销售额_std{window}"] = (
            weekly_sales["销售额"].rolling(window, min_periods=1).std().fillna(0)
        )
        weekly_sales[f"利润_ma{window}"] = (
            weekly_sales["利润"].rolling(window, min_periods=1).mean()
        )
        weekly_sales[f"利润_std{window}"] = (
            weekly_sales["利润"].rolling(window, min_periods=1).std().fillna(0)
        )

    weekly_sales["销售额_diff"] = weekly_sales["销售额"].diff().fillna(0)
    weekly_sales["利润_diff"] = weekly_sales["利润"].diff().fillna(0)
    weekly_sales["销售额_pct"] = weekly_sales["销售额"].pct_change().fillna(0).clip(-1, 1)
    weekly_sales["利润_pct"] = weekly_sales["利润"].pct_change().fillna(0).clip(-1, 1)
    return weekly_sales


SALES_FEATURES = [
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

PROFIT_FEATURES = [
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


def _train_models(train_data: pd.DataFrame) -> dict[str, Any]:
    sales_scaler_x = StandardScaler()
    sales_scaler_y = StandardScaler()
    profit_scaler_x = StandardScaler()
    profit_scaler_y = StandardScaler()
    sales_model = Ridge(alpha=10.0)
    profit_model = Ridge(alpha=10.0)

    sales_x = train_data[SALES_FEATURES].values
    sales_y = train_data["销售额"].values
    profit_x = train_data[PROFIT_FEATURES].values
    profit_y = train_data["利润"].values

    sales_x_scaled = sales_scaler_x.fit_transform(sales_x)
    sales_y_scaled = sales_scaler_y.fit_transform(sales_y.reshape(-1, 1)).ravel()
    profit_x_scaled = profit_scaler_x.fit_transform(profit_x)
    profit_y_scaled = profit_scaler_y.fit_transform(profit_y.reshape(-1, 1)).ravel()
    sales_model.fit(sales_x_scaled, sales_y_scaled)
    profit_model.fit(profit_x_scaled, profit_y_scaled)

    return {
        "sales_model": sales_model,
        "profit_model": profit_model,
        "sales_scaler_x": sales_scaler_x,
        "sales_scaler_y": sales_scaler_y,
        "profit_scaler_x": profit_scaler_x,
        "profit_scaler_y": profit_scaler_y,
        "sales_r2": r2_score(sales_y_scaled, sales_model.predict(sales_x_scaled)),
        "profit_r2": r2_score(profit_y_scaled, profit_model.predict(profit_x_scaled)),
    }


def _generate_forecast(
    weekly_sales: pd.DataFrame,
    train_data: pd.DataFrame,
    forecast_weeks: int,
    model_state: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    last_week = train_data.iloc[-1]
    last_date = weekly_sales["日期"].max()
    sales_history = list(train_data["销售额"].values)
    profit_history = list(train_data["利润"].values)
    forecast_results = []

    for index in range(1, forecast_weeks + 1):
        future_date = last_date + pd.Timedelta(weeks=index)
        sales_features, profit_features = _build_future_features(
            future_date,
            int(last_week["周序号"] + index),
            sales_history,
            profit_history,
        )
        sales_scaled = model_state["sales_scaler_x"].transform([sales_features])
        profit_scaled = model_state["profit_scaler_x"].transform([profit_features])
        sales_prediction = model_state["sales_model"].predict(sales_scaled)
        profit_prediction = model_state["profit_model"].predict(profit_scaled)
        sales = float(
            model_state["sales_scaler_y"].inverse_transform(sales_prediction.reshape(-1, 1))[0][0]
        )
        profit = float(
            model_state["profit_scaler_y"].inverse_transform(profit_prediction.reshape(-1, 1))[0][0]
        )
        sales_history.append(sales)
        profit_history.append(profit)
        forecast_results.append(
            {
                "week": index,
                "date": future_date.strftime("%Y-%m-%d"),
                "sales": round(sales, 2),
                "profit": round(profit, 2),
                "profit_rate": round((profit / sales * 100) if sales else 0.0, 2),
            }
        )

    total_sales = sum(item["sales"] for item in forecast_results)
    total_profit = sum(item["profit"] for item in forecast_results)
    return forecast_results, {
        "total_sales": round(total_sales, 2),
        "total_profit": round(total_profit, 2),
        "avg_profit_rate": round((total_profit / total_sales * 100) if total_sales else 0.0, 2),
    }


def _build_future_features(
    future_date,
    future_week_idx: int,
    sales_history: list[float],
    profit_history: list[float],
) -> tuple[list[float], list[float]]:
    month = future_date.month
    quarter = (month - 1) // 3 + 1

    def lag(series: list[float], offset: int) -> float:
        return float(series[-offset]) if len(series) >= offset else 0.0

    def moving_average(series: list[float], window: int) -> float:
        return float(np.mean(series[-window:])) if series else 0.0

    def std(series: list[float], window: int) -> float:
        return float(np.std(series[-window:])) if series else 0.0

    def diff(series: list[float]) -> float:
        return float(series[-1] - series[-2]) if len(series) >= 2 else 0.0

    def pct(series: list[float]) -> float:
        if len(series) >= 2 and series[-2] != 0:
            return float(np.clip((series[-1] - series[-2]) / series[-2], -1, 1))
        return 0.0

    base = [
        future_week_idx,
        np.sin(2 * np.pi * month / 12),
        np.cos(2 * np.pi * month / 12),
        np.sin(2 * np.pi * quarter / 4),
        np.cos(2 * np.pi * quarter / 4),
        int(future_date.day <= 7),
        int(future_date.day >= 24),
    ]
    sales_features = base + [
        lag(sales_history, 1),
        lag(sales_history, 2),
        lag(sales_history, 3),
        lag(sales_history, 4),
        moving_average(sales_history, 3),
        moving_average(sales_history, 4),
        moving_average(sales_history, 6),
        std(sales_history, 3),
        diff(sales_history),
        pct(sales_history),
    ]
    profit_features = base + [
        lag(profit_history, 1),
        lag(profit_history, 2),
        lag(profit_history, 3),
        lag(profit_history, 4),
        moving_average(profit_history, 3),
        moving_average(profit_history, 4),
        moving_average(profit_history, 6),
        std(profit_history, 3),
        diff(profit_history),
        pct(profit_history),
        lag(sales_history, 1),
    ]
    return sales_features, profit_features
