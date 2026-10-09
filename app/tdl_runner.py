import codecs
import os
import re
from typing import Callable, Optional

from PySide6.QtCore import QProcess


class TdlRunner:
    """
    使用 QProcess 管理 tdl 子进程，不阻塞 GUI 事件循环。
    """

    def __init__(self, tdl_path: str):
        self._tdl_path = tdl_path
        self._process: Optional[QProcess] = None
        self._stdout_decoder = None
        self._stderr_decoder = None
        self._stdout_pending = ""
        self._stderr_pending = ""

        # 回调
        self.on_stdout: Optional[Callable[[str], None]] = None
        self.on_stderr: Optional[Callable[[str], None]] = None
        self.on_exit: Optional[Callable[[int], None]] = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() == QProcess.ProcessState.Running

    def start(self, args: list) -> None:
        """启动 tdl 进程。args 不包含 tdl.exe 路径。"""
        if self.is_running:
            return

        self._process = QProcess()
        self._process.setProgram(self._tdl_path)
        self._process.setArguments(args)
        self._stdout_decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._stderr_decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._stdout_pending = ""
        self._stderr_pending = ""
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self._process.readyReadStandardError.connect(self._on_stderr_ready)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        

        try:
            self._process.setCreateProcessArgumentsModifier(
                lambda info: info.setCreateProcessFlags(0x08000000)
            )
        except Exception:
            pass

        self._process.start()

    def _emit_lines(self, stream: str, text: str, final: bool = False) -> None:
        pending_attr = f"_{stream}_pending"
        pending = getattr(self, pending_attr) + text
        parts = re.split(r"[\r\n]", pending)
        if final:
            complete, remainder = parts, ""
        else:
            complete, remainder = parts[:-1], parts[-1]
        setattr(self, pending_attr, remainder)
        callback = self.on_stdout if stream == "stdout" else self.on_stderr
        if callback:
            for line in complete:
                if line:
                    callback(line)

    def _on_stdout_ready(self):
        if self._process and self.on_stdout:
            data = bytes(self._process.readAllStandardOutput())
            text = self._stdout_decoder.decode(data, final=False)
            self._emit_lines("stdout", text)

    def _on_stderr_ready(self):
        if self._process and self.on_stderr:
            data = bytes(self._process.readAllStandardError())
            text = self._stderr_decoder.decode(data, final=False)
            self._emit_lines("stderr", text)

    def _flush_output(self) -> None:
        if self._stdout_decoder is not None:
            self._emit_lines("stdout", self._stdout_decoder.decode(b"", final=True), final=True)
            self._stdout_decoder = None
        if self._stderr_decoder is not None:
            self._emit_lines("stderr", self._stderr_decoder.decode(b"", final=True), final=True)
            self._stderr_decoder = None

    def _on_error(self, error):
        error_text = self._process.errorString() if self._process else str(error)
        if self.on_stderr:
            self.on_stderr(f"[进程错误] {error_text}")

    def _on_finished(self, exit_code: int, exit_status):
        # 读取剩余输出
        self._on_stdout_ready()
        self._on_stderr_ready()
        self._flush_output()
        if self.on_exit:
            self.on_exit(exit_code)

    def stop(self) -> None:
        """停止进程（整棵树）。"""
        if self._process:
            proc = self._process
            pid = proc.processId()
            if pid > 0 and proc.state() == QProcess.ProcessState.Running:
                try:
                    import subprocess
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True, timeout=5,
                    )
                except Exception:
                    proc.kill()
            self._process = None

    def __del__(self):
        try:
            self.stop()
        except (RuntimeError, AttributeError):
            pass
