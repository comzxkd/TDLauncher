import re
from dataclasses import dataclass
from typing import Optional, Literal

EventType = Literal["PROGRESS", "DONE", "ERROR", "META", "IGNORED"]

@dataclass
class TdlEvent:
    type: EventType
    raw: str
    
    # 文件层
    descriptor: str = ""      # e.g. "ASMR基佬中心(1539428348):19281"
    channel_name: str = ""    # e.g. "ASMR基佬中心"
    peer_id: str = ""         # e.g. "1539428348"
    msg_id: str = ""          # e.g. "19281"
    
    # 进度层
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    
    # 错误层
    error_msg: str = ""

class StateParser:
    """
    Tdl 核心解析中枢 (State Machine)
    将 Tdl CLI 杂乱的文本输出转化为结构化的 TdlEvent。
    """
    def __init__(self):
        # ANSI 转义清洗
        self._ansi_escape = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
        
        # 匹配完成行：ASMR基佬中心(1539428348):19281 ->~ ... done! [4.76 MB in 1.936s; 2.42 MB/s]
        self._re_done = re.compile(r"^(.*?)\s*(?:->|→|->~|-~).*?(?:done!|failed!)(?:\s*\[(.*?)\])?", re.IGNORECASE)
        
        # 匹配进度行：ASMR基佬中心(1539428348):19281 -> ... 55% [===>  ] 2.4 MB/s ETA 3s
        # 注意 tdl 的格式可能不带 ->，直接是 名字 55%
        self._re_prog = re.compile(r"^(.*?)\s+(?P<pct>\d+(?:\.\d+)?)%\s*\[", re.IGNORECASE)
        
        # 提取速度和ETA
        self._re_speed = re.compile(r"(\d+(?:\.\d+)?\s*[KMG]?B/s)", re.IGNORECASE)
        self._re_eta = re.compile(r"ETA[:：]?\s*([0-9][0-9hmsHMS.:]+)", re.IGNORECASE)
        
        # 提取描述符内部的 (peer):msg 结构
        self._re_identity = re.compile(r"^(.*?)\((?P<peer>\d+)\):(?P<msg>\d+)$")

    def feed(self, text: str) -> TdlEvent:
        clean = self._ansi_escape.sub("", text).strip()
        if not clean:
            return TdlEvent("IGNORED", text)
        
        low = clean.lower()

        # 1. 错误判定
        if any(k in low for k in ("error", "flood", "failed", "panic")) or "失败" in clean:
            # 尝试提纯错误信息
            m = re.search(r"(?:Error|error|FAILED|failed):\s*(.*)", clean)
            err = m.group(1).strip() if m else clean
            return TdlEvent("ERROR", clean, error_msg=err)

        # 2. Meta 判定
        if clean.startswith("All files will be downloaded to"):
            return TdlEvent("META", clean)
        if clean.startswith("CPU:"):
            return TdlEvent("IGNORED", clean)

        # 3. Done 判定
        if "done!" in low or "failed!" in low:
            # 去除可能包含的 100%
            m_done = self._re_done.search(clean)
            if m_done:
                desc = m_done.group(1).strip()
                ev = TdlEvent("DONE", clean, percent=100.0)
                self._fill_identity(ev, desc)
                
                # 如果后面中括号里带有平均速度
                stats = m_done.group(2)
                if stats:
                    sm = self._re_speed.search(stats)
                    if sm:
                        ev.speed = sm.group(1)
                return ev

        # 4. Progress 判定 (需要包含百分比)
        m_prog = self._re_prog.search(clean)
        if m_prog:
            desc = m_prog.group(1).strip()
            # 清理 desc 中可能带有的 -> 等连接符
            desc = re.split(r"\s*(?:->|→|->~|-~)\s*", desc)[0].strip()
            
            ev = TdlEvent("PROGRESS", clean)
            ev.percent = float(m_prog.group("pct"))
            self._fill_identity(ev, desc)
            
            # 抓速度和 ETA
            sm = self._re_speed.search(clean)
            if sm:
                ev.speed = sm.group(1)
            em = self._re_eta.search(clean)
            if em:
                ev.eta = em.group(1)
                
            return ev

        # 如果没有特征，原样返回 META 留作日志
        return TdlEvent("META", clean)

    def _fill_identity(self, ev: TdlEvent, raw_desc: str):
        # 兼容纯数字
        if raw_desc.isdigit():
            ev.descriptor = f"#{raw_desc}"
            ev.msg_id = raw_desc
            return
            
        ev.descriptor = raw_desc
        # 切割 ASMR基佬中心(1539428348):19281
        m = self._re_identity.match(raw_desc)
        if m:
            ev.channel_name = m.group(1).strip()
            ev.peer_id = m.group("peer")
            ev.msg_id = m.group("msg")
