"""
TTS 语音合成服务 - 使用 Edge-TTS
"""

import logging
from pathlib import Path

import edge_tts

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TTSService:
    """Edge-TTS 语音合成服务"""

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        """
        初始化TTS服务

        Args:
            voice: 语音名称，默认使用中文女声
                   可选: zh-CN-XiaoxiaoNeural, zh-CN-YunxiNeural, zh-CN-YunyangNeural
        """
        self.voice = voice

    async def synthesize(
        self, text: str, output_path: str, voice: str = None, rate: str = "+0%", volume: str = "+0%"
    ):
        """
        合成语音

        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径（.mp3）
            voice: 语音名称 (可选)
            rate: 语速 (例如 "+0%", "+20%")
            volume: 音量 (例如 "+0%", "-10%")
        """
        logger.info("[TTS Service] 开始语音合成")
        logger.info(f"[TTS Service] 文本长度: {len(text)} 字符")
        logger.info(f"[TTS Service] 输出路径: {output_path}")

        try:
            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[TTS Service] 输出目录已确保存在: {output_file.parent}")

            selected_voice = voice or self.voice
            logger.info(f"[TTS Service] 选择语音: {selected_voice}")
            logger.info(f"[TTS Service] 语速: {rate}, 音量: {volume}")

            # 创建TTS通信对象
            logger.info("[TTS Service] 创建 Edge-TTS Communicate 对象")
            communicate = edge_tts.Communicate(text, selected_voice, rate=rate, volume=volume)

            # 保存音频文件
            logger.info("[TTS Service] 开始调用 Edge-TTS API 生成音频...")
            await communicate.save(str(output_file))
            logger.info("[TTS Service] Edge-TTS API 调用完成")

            # 验证文件是否生成
            if output_file.exists():
                file_size = output_file.stat().st_size
                logger.info(
                    f"[TTS Service] ✅ 语音合成成功! 文件: {output_path}, 大小: {file_size} bytes"
                )
                logger.info(
                    f"[TTS Service] 使用语音: {selected_voice}, 语速: {rate}, 音量: {volume}"
                )
            else:
                logger.error(f"[TTS Service] ❌ 音频文件未生成: {output_path}")
                raise Exception("音频文件未生成")

            return True
        except Exception as e:
            logger.error(f"[TTS Service] ❌ TTS 合成失败: {str(e)}", exc_info=True)
            raise

    async def list_voices(self) -> list:
        """获取可用的语音列表"""
        voices = await edge_tts.list_voices()
        return [
            {
                "name": v["Name"],
                "short_name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"],
            }
            for v in voices
            if v["Locale"].startswith("zh-")  # 只返回中文语音
        ]
