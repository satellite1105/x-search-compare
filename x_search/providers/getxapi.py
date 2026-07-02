"""GetXAPI プロバイダー。

GetXAPI Advanced Search の公式仕様確認済み:
- GET https://api.getxapi.com/twitter/tweet/advanced_search
- 認証: Authorization: Bearer {api_key}
- パラメータ: q (検索語), product (Latest または Top), cursor (ページネーション用)
- limit / count / max のような取得件数指定パラメータは存在しない。
- 1 API call あたり最大20 tweets/page。

TODO: cursor によるページネーションは未対応。複数ページ取得したい場合は要実装。
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

    GetXAPI は queryType ではなく product パラメータで Top/Latest を指定する。
    limit はAPIには渡さない（該当パラメータが存在しないため）。呼び出し側で
    normalized.json への切り詰めに使う。

    TODO: cursor によるページネーションは未対応（1ページ最大20件のみ取得）。
    TODO: レート制限の仕様は公式ドキュメントで未確認。
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    params = {
        "q": query,
        "product": query_type,
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
