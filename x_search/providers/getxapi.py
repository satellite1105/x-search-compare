"""GetXAPI プロバイダー。

TODO: 実際のエンドポイントURLとレスポンス仕様は GetXAPI のドキュメントを参照して確認すること。
参考: https://getxapi.com/docs (ドキュメントURLは要確認)

現在の実装は公開情報をもとにした推定であり、実際のレスポンス構造と異なる場合がある。
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Optional

from x_search.normalize import NormalizedTweet


def _parse_created_at(raw_date: str) -> str:
    try:
        dt = datetime.strptime(raw_date, "%a %b %d %H:%M:%S +0000 %Y")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return raw_date

_BASE_URL = "https://api.getxapi.com"


def search(query: str, limit: int, api_key: str, query_type: str = "Latest") -> tuple[list[dict], Optional[str]]:
    """
    X検索を実行し (raw レスポンスリスト, エラーメッセージ) を返す。

    エラー時は ([], エラーメッセージ文字列) を返す。

    TODO: 以下を公式ドキュメントで確認する:
    - 正確なエンドポイントパス
    - 認証方式 (Authorizationヘッダー or クエリパラメータ)
    - ページネーションパラメータ名
    - レート制限の仕様
    - queryType の指定値・挙動 (Top/Latest で公式ドキュメント通りか要確認)
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    params = {
        "q": query,
        "queryType": query_type,
    }

    try:
        response = httpx.get(
            f"{_BASE_URL}/twitter/tweet/advanced_search",
            headers=headers,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        # TODO: レスポンスのキー構造を確認する
        tweets = data.get("data", data.get("tweets", data.get("results", [])))
        return tweets, None
    except httpx.HTTPStatusError as e:
        return [], f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except httpx.RequestError as e:
        return [], f"Request error: {e}"
    except Exception as e:
        return [], f"Unexpected error: {e}"


def normalize(raw: dict) -> NormalizedTweet:
    author = raw.get("author", {})
    return NormalizedTweet(
        id=str(raw.get("id", "")),
        text=raw.get("text", ""),
        url=raw.get("url", ""),
        author_username=author.get("userName", ""),
        author_name=author.get("name", ""),
        created_at=_parse_created_at(raw.get("createdAt", "")),
        like_count=raw.get("likeCount"),
        repost_count=raw.get("retweetCount"),
        reply_count=raw.get("replyCount"),
        view_count=raw.get("viewCount"),
        source="getxapi",
    )
