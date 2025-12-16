import numpy as np
import webrtcvad


class SimpleMyVoiceProcessor:
    """
    简单版本地音频处理器：
    - 使用 WebRTC VAD 过滤掉大部分静音和非语音段
    - 目前不做复杂降噪，仅作为后续升级的挂载点
    """

    def __init__(self, sample_rate: int = 16000, frame_ms: int = 20, vad_aggressiveness: int = 2):
        """
        Args:
            sample_rate: 采样率，必须是 WebRTC VAD 支持的值之一（8k/16k/32k/48k）
            frame_ms: VAD 帧长，只能是 10 / 20 / 30 ms
            vad_aggressiveness: 0-3，数值越大越"挑剔"，越容易判定为非语音
        """
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.vad = webrtcvad.Vad(vad_aggressiveness)

        # 16bit（2字节）单声道
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * 2

    def _denoise(self, pcm_int16: np.ndarray) -> np.ndarray:
        """
        占位降噪函数：
        如需更强降噪，可在这里接入 rnnoise / deepfilterNet 等模型。
        当前直接返回原始数据。
        """
        return pcm_int16

    def process(self, pcm_chunk: np.ndarray):
        """
        处理一段来自 sounddevice 的 PCM 音频数据。

        输入:
            pcm_chunk: numpy 数组，dtype=int16，shape: (N, 1) 或 (N,)
        输出:
            - 返回 np.ndarray(int16, shape: (N, 1)) 表示“通过过滤”的音频
            - 返回 None 表示这段被判定为静音/噪声，将被上层丢弃
        """
        if pcm_chunk is None:
            return None

        # 转成一维 mono int16
        mono = np.asarray(pcm_chunk).reshape(-1).astype(np.int16)

        if mono.size == 0:
            return None

        # 简单占位降噪（目前尚未启用复杂模型）
        mono = self._denoise(mono)

        bytes_data = mono.tobytes()
        if len(bytes_data) < self.frame_bytes:
            # 太短的帧不做判定，直接丢弃，避免 VAD 报错
            return None

        # 取中间的一帧做 VAD 判定（简单但通常足够）
        mid = len(bytes_data) // 2
        start = max(0, mid - self.frame_bytes // 2)
        frame = bytes_data[start:start + self.frame_bytes]

        try:
            is_speech = self.vad.is_speech(frame, self.sample_rate)
        except Exception:
            # 任意异常都视作非语音，避免影响主流程
            return None

        if not is_speech:
            # 判定为非语音：不发送到后端
            return None

        # 判定为语音：返回原始（或已降噪）音频，保持列向量形状
        return mono.reshape(-1, 1)


