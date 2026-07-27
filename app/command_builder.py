import os
import shlex
from typing import List, Optional

from link_parser import ParsedLink
from config import Config


def build_download_commands(
    url: str,
    parsed: ParsedLink,
    config: Config,
    include_comments: bool = False,
) -> List[List[str]]:
    """
    构建一组 tdl 命令（每个命令是一个参数列表）。
    返回一个列表，每个元素是一个命令的参数列表，用于依次执行。
    """
    commands: List[List[str]] = []

    # ---------- 第一步：下载帖子 ----------
    dl_args = _build_dl_args(url, config)
    commands.append(dl_args)

    # ---------- 第二步：评论区下载 ----------
    if include_comments and parsed.kind in ("public_post", "private_post"):
        # 检查是否已经是评论链接
        if parsed.comment_id is not None:
            pass  # 已经是评论链接，跳过评论区下载
        else:
            comment_cmds = _build_comment_commands(parsed, config)
            commands.extend(comment_cmds)

    return commands


def _build_dl_args(url: str, config: Config) -> List[str]:
    """构建 tdl dl 的参数列表"""
    args = ["dl", "-u", url]

    # 目录
    args += ["-d", config.download_dir]

    # 代理
    if config.proxy_enabled and config.proxy:
        args += ["--proxy", config.proxy]

    # 线程和并发
    args += ["-t", str(config.threads)]
    args += ["-l", str(config.limit)]

    # 文件名模板
    if config.filename_template:
        args += ["--template", config.filename_template]

    # 内容过滤
    ext_map = {
        "images": "jpg,png,gif,webp,jpeg",
        "videos": "mp4,mkv,mov,avi,webm,flv",
        "audio": "mp3,ogg,wav,flac,aac,m4a,wma",
    }
    if config.content_type in ext_map:
        args += ["-i", ext_map[config.content_type]]
    elif config.content_type == "custom" and config.custom_extensions:
        args += ["-i", config.custom_extensions]

    # 选项
    if config.skip_same:
        args += ["--skip-same"]
    if config.resume:
        args += ["--continue"]
    if config.takeout:
        args += ["--takeout"]
    if config.group:
        args += ["--group"]

    return args


def _build_comment_commands(parsed: ParsedLink, config: Config) -> List[List[str]]:
    """
    构建评论区下载命令：
     1. tdl chat export -c <channel> --reply <msg_id> -o tmp.json
     2. tdl dl -f tmp.json -d <dir>
    """
    tmp_json = os.path.join(config.download_dir, f"_comments_{parsed.message_id}.json")

    # 确定 chat 标识
    chat_identifier = parsed.channel if parsed.channel else parsed.chat_id

    # export 命令：导出所有媒体（过滤在 dl 阶段做）
    export_args = [
        "chat", "export",
        "-c", chat_identifier,
        "--reply", str(parsed.message_id),
        "-o", tmp_json,
    ]
    if config.proxy_enabled and config.proxy:
        export_args += ["--proxy", config.proxy]

    # 从 JSON 下载
    dl_args = _build_dl_args_for_json(tmp_json, config)

    return [export_args, dl_args]


def _build_dl_args_for_json(json_path: str, config: Config) -> List[str]:
    """构建基于 JSON 文件的 tdl dl 参数"""
    args = ["dl", "-f", json_path, "-d", config.download_dir]
    if config.proxy_enabled and config.proxy:
        args += ["--proxy", config.proxy]
    args += ["-t", str(config.threads)]
    args += ["-l", str(config.limit)]
    if config.filename_template:
        args += ["--template", config.filename_template]
    if config.skip_same:
        args += ["--skip-same"]
    if config.resume:
        args += ["--continue"]
    if config.takeout:
        args += ["--takeout"]
    return args
