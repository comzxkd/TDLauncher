import os
from typing import Callable, Optional

from PySide6.QtCore import QProcess


class TdlRunner:
    """
    使用 QProcess 管理 tdl 子进程，不阻塞 GUI 事件循环。
    """

    def __init__(self, tdl_path: str):
        self._tdl_path = tdl_path
        self._process: Optional[QProcess] = None

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

    def _on_stdout_ready(self):
        if self._process and self.on_stdout:
            data = self._process.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            for line in text.split("\n"):
                stripped = line.rstrip("\r\n")
                if stripped:
                    self.on_stdout(stripped)

    def _on_stderr_ready(self):
        if self._process and self.on_stderr:
            data = self._process.readAllStandardError()
            text = bytes(data).decode("utf-8", errors="replace")
            for line in text.split("\n"):
                stripped = line.rstrip("\r\n")
                if stripped:
                    self.on_stderr(stripped)

    def _on_error(self, error):
        error_text = self._process.errorString() if self._process else str(error)
        if self.on_stderr:
            self.on_stderr(f"[进程错误] {error_text}")

    def _on_finished(self, exit_code: int, exit_status):
        # 读取剩余输出
        self._on_stdout_ready()
        self._on_stderr_ready()
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
