import re
from typing import Optional


class ProgressParser:
    """
    从 tdl 的 stdout/stderr 中提取下载进度。
    """

    def __init__(self):
        self._percent_pattern = re.compile(r"(?P<percent>\d+(?:\.\d+)?)%")
        self._speed_pattern = re.compile(r";\s*(?P<speed>[^\]]+/s)\]")
        self._error_pattern = re.compile(r"(?:Error|error|FAILED|failed):\s*(.*)")
        self.reset()

    def reset(self) -> None:
        self.percent: Optional[float] = None
        self.speed: Optional[str] = None
        self.error: Optional[str] = None

    def feed(self, text: str) -> None:
        """输入 tdl 输出的原始文本行，尝试提取进度。"""
        cleaned = self._strip_ansi(text)

        m = self._percent_pattern.search(cleaned)
        if m:
            self.percent = float(m.group("percent"))

        m = self._speed_pattern.search(cleaned)
        if m:
            self.speed = m.group("speed").strip()

        m = self._error_pattern.search(cleaned)
        if m:
            self.error = m.group(1).strip()

    def summary(self) -> str:
        """返回可读的进度字符串。"""
        parts = []
        if self.percent is not None:
            parts.append(f"{self.percent:.1f}%")
        if self.speed:
            parts.append(self.speed)
        if parts:
            return " | ".join(parts)
        return "等待中..."

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """去掉 ANSI 转义序列。"""
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
