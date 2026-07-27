import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedLink:
    """解析结果"""
    raw_url: str
    kind: str  # public_post | private_post | comment | thread | unknown
    channel: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[int] = None
    comment_id: Optional[int] = None
    thread_id: Optional[int] = None

    def display(self) -> str:
        """生成人类可读的识别结果"""
        if self.kind == "public_post":
            return f"📎 普通帖子: 频道 @{self.channel} 消息 #{self.message_id}"
        elif self.kind == "private_post":
            return f"📎 私有频道: ID {self.chat_id} 消息 #{self.message_id}"
        elif self.kind == "comment":
            return f"💬 评论: 频道 @{self.channel} 帖子 #{self.message_id} 评论 #{self.comment_id}"
        elif self.kind == "thread":
            return f"🧵 话题: 频道 @{self.channel} 消息 #{self.message_id} 话题 #{self.thread_id}"
        else:
            return "⚠️ 无法识别的链接"


def parse_telegram_link(url: str) -> ParsedLink:
    """解析 Telegram 链接，返回 ParsedLink。"""
    url = url.strip().rstrip("/")

    # 私有频道: https://t.me/c/chat_id/message_id?comment=xxx
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)(?:\?.*)?$", url)
    if m:
        chat_id = m.group(1)
        msg_id = int(m.group(2))
        comment_id = _extract_query_param(url, "comment")
        if comment_id:
            return ParsedLink(
                raw_url=url, kind="comment",
                chat_id=chat_id, message_id=msg_id,
                comment_id=int(comment_id),
            )
        thread_id = _extract_query_param(url, "thread")
        if thread_id:
            return ParsedLink(
                raw_url=url, kind="thread",
                chat_id=chat_id, message_id=msg_id,
                thread_id=int(thread_id),
            )
        return ParsedLink(
            raw_url=url, kind="private_post",
            chat_id=chat_id, message_id=msg_id,
        )

    # 公开链接: https://t.me/channel/msg_id?comment=xxx
    m = re.match(r"https?://t\.me/([a-zA-Z0-9_]+)/(\d+)(?:\?.*)?$", url)
    if m:
        channel = m.group(1)
        msg_id = int(m.group(2))
        comment_id = _extract_query_param(url, "comment")
        if comment_id:
            return ParsedLink(
                raw_url=url, kind="comment",
                channel=channel, message_id=msg_id,
                comment_id=int(comment_id),
            )
        thread_id = _extract_query_param(url, "thread")
        if thread_id:
            return ParsedLink(
                raw_url=url, kind="thread",
                channel=channel, message_id=msg_id,
                thread_id=int(thread_id),
            )
        return ParsedLink(
            raw_url=url, kind="public_post",
            channel=channel, message_id=msg_id,
        )

    return ParsedLink(raw_url=url, kind="unknown")


def _extract_query_param(url: str, name: str) -> Optional[str]:
    m = re.search(r"[?&]" + name + r"=(\d+)", url)
    return m.group(1) if m else None
