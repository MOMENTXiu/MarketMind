"""Unit tests for report and voice abilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

from backend.abilities.report.generate_analysis_report import generate_analysis_report
from backend.abilities.report.generate_speech_text import generate_speech_text
from backend.abilities.voice.generate_broadcast_script import generate_broadcast_script
from backend.abilities.voice.synthesize_speech import synthesize_speech
from backend.providers.dtos import (
    LLMRequestDTO,
    LLMResponseDTO,
    SpeechSynthesisRequestDTO,
    SpeechSynthesisResultDTO,
)


@dataclass
class ProjectFixture:
    name: str = "Demo Project"
    dataset_filename: str = "dataset.csv"
    updated_at: datetime = datetime(2026, 5, 25, 10, 30)


@dataclass
class RuleFixture:
    antecedents: list[str]
    consequent: str
    support: float
    confidence: float
    lift: float
    strategy: str


class FakeLLMProvider:
    def __init__(self, text: str = "生成的播报文案", fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.requests: list[LLMRequestDTO] = []

    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("llm unavailable")
        return LLMResponseDTO(text=self.text, provider=request.provider, model=request.model)


class FakeSpeechProvider:
    def __init__(self) -> None:
        self.requests: list[SpeechSynthesisRequestDTO] = []

    async def synthesize(self, request: SpeechSynthesisRequestDTO) -> SpeechSynthesisResultDTO:
        self.requests.append(request)
        return SpeechSynthesisResultDTO(audio_path=request.output_path, audio_url="/audio/demo.mp3")

    async def list_voices(self) -> list[dict[str, str]]:
        return []


def make_results() -> dict:
    return {
        "association_rules": [
            RuleFixture(
                antecedents=["Milk", "Bread"],
                consequent="Cheese",
                support=0.4,
                confidence=0.8,
                lift=1.6,
                strategy="组合促销",
            )
        ],
        "prediction_data": {
            "sales_r2": 0.91,
            "profit_r2": 0.82,
            "train_samples": 8,
            "forecast_weeks": 2,
            "forecast_data": [
                {"week": 1, "sales": 1200.0, "profit": 240.0},
                {"week": 2, "sales": 1300.0, "profit": 260.0},
            ],
        },
        "clustering_data": {
            "total_customers": 6,
            "n_clusters": 2,
            "silhouette_score": 0.62,
            "cluster_profiles": [
                {
                    "cluster_name": "高价值活跃客户",
                    "customer_count": 4,
                    "avg_recency": 3,
                    "avg_frequency": 5,
                    "avg_monetary": 3000.0,
                    "avg_order_value": 600.0,
                    "marketing_strategy": "VIP专属优惠、会员积分加倍",
                }
            ],
        },
    }


def test_generate_analysis_report_keeps_current_sections_and_fields() -> None:
    report = generate_analysis_report(ProjectFixture(), make_results())

    assert "# Demo Project - 营销分析报告" in report
    assert "**数据集**: dataset.csv" in report
    assert "## 1. 关联规则分析" in report
    assert "Milk, Bread → **Cheese**" in report
    assert "销售额预测 R² 得分: 0.9100" in report
    assert "### 高价值活跃客户 (4人)" in report
    assert "本报告基于 Apriori 算法" in report


def test_generate_speech_text_keeps_current_summary_shape() -> None:
    speech = generate_speech_text(ProjectFixture(), make_results())

    assert "Demo Project营销分析报告播报" in speech
    assert "本次分析共发现1条关联规则" in speech
    assert "第1条规则：Milk、Bread，推荐搭配Cheese" in speech
    assert "销售预测模型训练完成" in speech
    assert "客户聚类分析将6位客户分为2个群体" in speech
    assert speech.endswith("报告播报完毕。")


@pytest.mark.anyio
async def test_generate_broadcast_script_uses_llm_provider_contract() -> None:
    provider = FakeLLMProvider(text="客户分析播报")

    script = await generate_broadcast_script(
        {"cluster_name": "高价值活跃客户"},
        provider,
        {
            "provider": "openai",
            "baseUrl": "https://example.test",
            "apiKey": "redacted",
            "modelName": "demo-model",
        },
        "summary",
    )

    assert script == "客户分析播报"
    assert provider.requests[0].provider == "openai"
    assert provider.requests[0].model == "demo-model"
    assert provider.requests[0].messages[0].role == "system"
    assert provider.requests[0].messages[1].content.startswith("数据：")


@pytest.mark.anyio
async def test_generate_broadcast_script_falls_back_when_provider_fails() -> None:
    provider = FakeLLMProvider(fail=True)

    script = await generate_broadcast_script(
        {
            "customer_name": "张三",
            "customer_id": "C1",
            "cluster_name": "普通活跃客户",
            "monetary": 1000,
            "frequency": 2,
            "recency": 5,
        },
        provider,
        {
            "provider": "openai",
            "baseUrl": "https://example.test",
            "apiKey": "redacted",
            "modelName": "demo-model",
        },
        "summary",
    )

    assert "客户张三-C1被分类为'普通活跃客户'" in script


@pytest.mark.anyio
async def test_synthesize_speech_uses_speech_provider_contract(tmp_path: Path) -> None:
    provider = FakeSpeechProvider()
    output_path = tmp_path / "demo.mp3"

    result = await synthesize_speech(
        "播报文本",
        output_path,
        provider,
        voice="zh-CN-XiaoxiaoNeural",
        rate="+10%",
        volume="+0%",
    )

    assert result.audio_path == output_path
    assert result.audio_url == "/audio/demo.mp3"
    assert provider.requests[0].text == "播报文本"
    assert provider.requests[0].voice == "zh-CN-XiaoxiaoNeural"
    assert provider.requests[0].rate == "+10%"
