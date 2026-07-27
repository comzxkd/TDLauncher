import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


@dataclass
class Config:
    download_dir: str = "D:/Downloads"
    proxy_enabled: bool = False
    proxy: str = "socks5://127.0.0.1:7897"
    threads: int = 8
    limit: int = 4
    content_type: str = "all"  # all | images | videos | custom
    custom_extensions: str = ""
    filename_template: str = "{{ filenamify .FileName }}"
    skip_same: bool = True
    resume: bool = False
    takeout: bool = False
    group: bool = True
    download_comments: bool = False
    auto_subfolder: bool = False
    window_width: int = 960
    window_height: int = 720

    @classmethod
    def load(cls) -> "Config":
        if not os.path.isfile(CONFIG_FILE):
            return cls()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = cls()
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
            return cfg
        except Exception:
            return cls()

    def save(self) -> None:
        data = asdict(self)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
