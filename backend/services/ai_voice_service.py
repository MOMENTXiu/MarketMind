"""
AI 语音播报服务 - LLM + Edge-TTS 智能语音生成
"""
import asyncio
import httpx
import edge_tts
from pathlib import Path
from typing import Dict, Any, List
import tempfile


class AIVoiceService:
    """AI 语音播报服务类"""

    VOICE_NAME = "zh-CN-YunxiNeural"  # 使用云希语音
    VOICE_RATE = "+0%"  # 语速
    VOICE_VOLUME = "+0%"  # 音量

    @staticmethod
    async def generate_script(data: Dict[str, Any], llm_config: Dict[str, str], scene_type: str) -> str:
        """
        使用 LLM 生成播报文案

        Args:
            data: 算法数据（JSON 格式）
            llm_config: LLM 配置 {provider, baseUrl, apiKey, modelName}
            scene_type: 场景类型 (clustering, association, prediction)

        Returns:
            LLM 生成的播报文案
        """
        # 根据场景类型构建 prompt
        prompts = {
            "clustering": "你是一位商业顾问。请将以下客户聚类分析数据转化为一段简短、专业、富有行动建议的中文播报词（50字以内）。重点突出该群体特征和营销策略建议。严禁输出代码或 JSON，只输出纯文字播报词。",
            "association": "你是一位商业顾问。请将以下商品关联规则数据转化为一段简短、专业、富有行动建议的中文播报词（50字以内）。重点突出商品关联性和销售建议。严禁输出代码或 JSON，只输出纯文字播报词。",
            "prediction": "你是一位商业顾问。请将以下销售预测数据转化为一段简短、专业、富有行动建议的中文播报词（50字以内）。重点突出未来趋势和备货建议。严禁输出代码或 JSON，只输出纯文字播报词。",
            "summary": "你是一位商业顾问。请将以下营销分析数据转化为一段简短、专业、富有行动建议的中文播报词（80字以内）。概括核心洞察和行动建议。严禁输出代码或 JSON，只输出纯文字播报词。"
        }

        system_prompt = prompts.get(scene_type, prompts["summary"])
        user_message = f"数据：{str(data)}"

        try:
            # 根据 provider 类型调用不同的 API
            if llm_config["provider"] == "claude":
                return await AIVoiceService._call_claude(
                    llm_config["baseUrl"],
                    llm_config["apiKey"],
                    llm_config["modelName"],
                    system_prompt,
                    user_message
                )
            else:  # openai 类型
                return await AIVoiceService._call_openai(
                    llm_config["baseUrl"],
                    llm_config["apiKey"],
                    llm_config["modelName"],
                    system_prompt,
                    user_message
                )
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            # 降级：返回简单的文案
            return AIVoiceService._generate_fallback_script(data, scene_type)

    @staticmethod
    async def _call_openai(base_url: str, api_key: str, model: str, system: str, user: str) -> str:
        """调用 OpenAI 类型 API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

    @staticmethod
    async def _call_claude(base_url: str, api_key: str, model: str, system: str, user: str) -> str:
        """调用 Claude API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "system": system,
                    "messages": [
                        {"role": "user", "content": user}
                    ],
                    "max_tokens": 200
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"].strip()

    @staticmethod
    def _generate_fallback_script(data: Dict[str, Any], scene_type: str) -> str:
        """降级文案生成（LLM 失败时使用）"""
        fallback_templates = {
            "clustering": "该客户群体具有独特的消费特征，建议采取针对性营销策略以提升转化率。",
            "association": "发现多组商品存在强关联关系，建议实施捆绑销售策略以提升客单价。",
            "prediction": "销售数据呈现上升趋势，建议提前备货以应对未来需求增长。",
            "summary": "本次分析揭示了重要的市场洞察，建议及时调整营销策略以把握商机。"
        }
        return fallback_templates.get(scene_type, fallback_templates["summary"])

    @staticmethod
    async def text_to_speech(
        text: str,
        output_path: str = None,
        voice: str = None,
        rate: str = None,
        volume: str = None
    ) -> str:
        """
        使用 Edge-TTS 将文本转换为语音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径（可选，默认使用临时文件）
            voice: 语音模型（可选，默认 zh-CN-YunxiNeural）
            rate: 语速（可选，默认 +0%）
            volume: 音量（可选，默认 +0%）

        Returns:
            音频文件路径
        """
        # 使用参数或默认值
        voice_name = voice or AIVoiceService.VOICE_NAME
        voice_rate = rate or AIVoiceService.VOICE_RATE
        voice_volume = volume or AIVoiceService.VOICE_VOLUME

        if not output_path:
            # 使用临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            output_path = temp_file.name
            temp_file.close()

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 使用 edge-tts 生成语音
        communicate = edge_tts.Communicate(
            text,
            voice_name,
            rate=voice_rate,
            volume=voice_volume
        )

        await communicate.save(output_path)
        return output_path

    @staticmethod
    async def generate_voice_broadcast(
        data: Dict[str, Any],
        llm_config: Dict[str, str],
        scene_type: str,
        output_dir: str = "backend/data/audio",
        tts_config: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        完整的 AI 语音播报流程（LLM + TTS）

        Args:
            data: 算法数据
            llm_config: LLM 配置
            scene_type: 场景类型
            output_dir: 输出目录
            tts_config: TTS 配置 {voice, rate, volume}

        Returns:
            {
                "success": bool,
                "text": str,  # LLM 生成的文案
                "audio_path": str,  # 音频文件路径
                "error": str  # 错误信息（如果失败）
            }
        """
        try:
            # 第一步：LLM 生成文案
            script = await AIVoiceService.generate_script(data, llm_config, scene_type)

            # 第二步：TTS 语音合成
            output_path = Path(output_dir) / f"{scene_type}_{hash(script) % 100000}.mp3"

            # 提取 TTS 配置
            voice = tts_config.get('voice') if tts_config else None
            rate = tts_config.get('rate') if tts_config else None
            volume = tts_config.get('volume') if tts_config else None

            audio_path = await AIVoiceService.text_to_speech(
                script,
                str(output_path),
                voice=voice,
                rate=rate,
                volume=volume
            )

            return {
                "success": True,
                "text": script,
                "audio_path": audio_path
            }

        except Exception as e:
            print(f"AI 语音播报失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "audio_path": ""
            }
