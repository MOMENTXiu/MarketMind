"""
TTS 语音合成服务 - 使用 Edge-TTS
"""
import edge_tts
from pathlib import Path


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

    async def synthesize(self, text: str, output_path: str):
        """
        合成语音

        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径（.mp3）
        """
        try:
            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 创建TTS通信对象
            communicate = edge_tts.Communicate(text, self.voice)

            # 保存音频文件
            await communicate.save(str(output_file))

            print(f"语音合成成功: {output_path}")
            return True

        except Exception as e:
            print(f"语音合成失败: {e}")
            raise e

    async def list_voices(self) -> list:
        """获取可用的语音列表"""
        voices = await edge_tts.list_voices()
        return [
            {
                "name": v["Name"],
                "short_name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"]
            }
            for v in voices
            if v["Locale"].startswith("zh-")  # 只返回中文语音
        ]
