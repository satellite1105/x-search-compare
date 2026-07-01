"""正規化後のツイートデータ構造の定義とユーティリティ。"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class NormalizedTweet:
    id: str
    text: str
    url: str
    author_username: str
    author_name: str
    created_at: str          # ISO 8601 形式 (例: "2024-01-01T12:00:00Z")
    like_count: Optional[int]
    repost_count: Optional[int]
    reply_count: Optional[int]
    view_count: Optional[int]
    source: str              # "twitterapi_io" or "getxapi"

    def to_dict(self) -> dict:
        return asdict(self)
