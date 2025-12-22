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

    VOICE_NAME = "zh-CN-XiaoxiaoNeural"  # 使用晓晓语音（女声）
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
            "clustering": """你是一位资深零售数据分析师。请将以下客户聚类分析数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明这是哪个客户群体，有多少人
2. 描述该群体的核心消费特征（用具体数字）
3. 给出2-3条具体的营销建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
            "association": """你是一位资深零售数据分析师。请将以下商品关联规则分析数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明发现了哪些商品关联
2. 用具体数字说明关联强度
3. 给出具体的捆绑销售建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
            "prediction": """你是一位资深零售数据分析师。请将以下销售预测数据转化为一段专业的营销播报词（100-150字）。

播报要求：
1. 说明预测的时间范围和趋势
2. 用具体数字描述预测结果
3. 给出备货和促销建议
4. 用商业播报的语气，简洁有力

严禁输出代码、JSON或markdown格式，只输出纯文字播报内容。""",
            "summary": """你是一位专业数据分析师，正在为管理团队提供客户分析报告。

关键要求：
1. 严格禁止使用："各位同事"、"大家好"、"请注意"、"亲爱的"等任何客套话或开场白
2. 必须直接以核心发现开头，格式："客户[姓名-ID]被分类为'[分群名称]'，其消费行为特征如下："
3. 采用三段式结构，每段简洁有力：
   - 【核心现状】用具体数字描述客户的RFM特征和消费水平
   - 【关键洞察】基于分群特征，分析该客户的价值潜力和行为模式
   - 【行动方案】给出2-3条具体可执行的营销建议，包含预期效果

4. 控制在80-120字以内
5. 严禁输出代码、JSON、markdown格式或任何非文本内容

输出示例风格："客户张三-4695被分类为'普通活跃客户'，其消费行为特征如下：最近30天内购买，累计消费12次，客单价约500元。该客户属于中等价值稳定型，复购意愿强但客单价有提升空间。建议：1)推送高价值商品组合优惠，提升客单价至800元；2)设置会员专属福利，巩固忠诚度；3)定期发送个性化推荐，预计可提升20%消费额。"""
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
                    "max_tokens": 400,
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
                    "max_tokens": 400
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"].strip()

    @staticmethod
    def _generate_fallback_script(data: Dict[str, Any], scene_type: str) -> str:
        """降级文案生成（LLM 失败时使用）"""

        if scene_type == "clustering":
            cluster_name = data.get("cluster_name", "客户群体")
            customer_count = data.get("customer_count", "若干")
            avg_order = data.get("avg_order_value", 0)
            recency = data.get("recency", 0)
            frequency = data.get("frequency", 0)
            strategy = data.get("marketing_strategy", "采取针对性营销策略")

            return f"""根据RFM聚类分析，识别出{cluster_name}，共{customer_count}位客户，最近消费距今{recency}天，平均消费{frequency}次，客单价{avg_order}元。建议{strategy}，通过优化商品推荐和专属优惠活动，提升该群体的复购率和客单价。"""

        elif scene_type == "association":
            return f"""通过商品关联规则分析，发现多组商品存在显著购买关联性，支持度和置信度均达标。建议将关联商品就近摆放，推出组合促销套餐，预计可提升15%到25%的连带销售率，并在收银台设置关联商品提醒。"""

        elif scene_type == "prediction":
            return f"""基于时间序列预测模型，销售数据呈现季节性波动和上升趋势，预计未来销量保持稳定增长。建议提前做好库存准备，确保热销商品充足供应，关注天气和节假日因素，灵活调整备货和促销策略。"""

        else:  # summary
            # 提取客户信息
            customer_name = data.get("customer_name", "客户")
            customer_id = data.get("customer_id", "未知")
            cluster_name = data.get("cluster_name", "客户群体")
            monetary = data.get("monetary", 0)
            frequency = data.get("frequency", 0)
            recency = data.get("recency", 0)

            # 计算客单价
            avg_order = monetary / frequency if frequency > 0 else 0

            return f"""客户{customer_name}-{customer_id}被分类为'{cluster_name}'，其消费行为特征如下：最近{recency}天购买，累计消费{frequency}次，客单价约{avg_order:.0f}元。该客户属于稳定型消费者，复购意愿较强。建议：1)推送个性化商品推荐，提升客单价；2)设置会员专属福利，巩固忠诚度；3)定期触达维护客户关系，预计可提升15%消费额。"""

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
            voice: 语音模型（可选，默认 zh-CN-XiaoxiaoNeural）
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

        try:
            # 使用 edge-tts 生成语音
            communicate = edge_tts.Communicate(
                text,
                voice_name,
                rate=voice_rate,
                volume=voice_volume
            )

            await communicate.save(output_path)
            return output_path
        except Exception as e:
            error_msg = str(e)
            if "No audio was received" in error_msg:
                raise Exception(
                    "Edge-TTS 服务暂时不可用，可能是网络连接问题。"
                    "请检查网络连接或稍后再试。"
                )
            else:
                raise Exception(f"TTS 合成失败: {error_msg}")

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
