#!/usr/bin/env python3
"""
X検索結果を twitterapi.io と GetXAPI で比較するスクリプト。

使い方:
  python compare_search.py "検索語" [--limit N] [--provider {twitterapi_io,getxapi,both}] [--query-type {Top,Latest}]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv

from x_search.providers import twitterapi_io, getxapi

load_dotenv()

_SENSITIVE_ENV_VARS = ("TWITTERAPI_IO_KEY", "GETXAPI_KEY")


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    env_key: str
    search: Callable
    normalize: Callable


_REGISTRY: list[ProviderSpec] = [
    ProviderSpec("twitterapi_io", "TWITTERAPI_IO_KEY", twitterapi_io.search, twitterapi_io.normalize),
    ProviderSpec("getxapi", "GETXAPI_KEY", getxapi.search, getxapi.normalize),
]


def _sanitize_dirname(query: str) -> str:
    slug = re.sub(r"[^\w\-]", "_", query)[:50]
    return slug or "_"


def _make_output_dir(query: str, query_type: str) -> Path:
    # マイクロ秒まで含めて同一秒・同一クエリでの上書きを防ぐ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dirname = f"{timestamp}_{_sanitize_dirname(query)}_{query_type}"
    output_dir = Path(__file__).parent / "data" / dirname
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _sanitize_str(text: str) -> str:
    """既知のAPIキー値を error.json に書き出す前にマスクする。"""
    for env_var in _SENSITIVE_ENV_VARS:
        value = os.getenv(env_var, "")
        if value and len(value) >= 8:
            text = text.replace(value, "***REDACTED***")
    return text


def _save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> 保存: {path}")


def _run_provider(spec: ProviderSpec, query: str, limit: int, api_key: str, output_dir: Path, query_type: str) -> None:
    provider_dir = output_dir / spec.name
    provider_dir.mkdir(exist_ok=True)

    def save_error(msg: str) -> None:
        _save_json(provider_dir / "error.json", {
            "provider": spec.name,
            "query": query,
            "query_type": query_type,
            "error": _sanitize_str(msg),
        })

    print(f"\n[{spec.name}] 検索中: '{query}' (limit={limit}, queryType={query_type})")
    raw_list, error = spec.search(query, limit, api_key, query_type)

    if error:
        print(f"  [エラー] {_sanitize_str(error)}")
        save_error(error)
        return

    # search() が list[dict] 以外を返した場合はクラッシュさせず error.json に記録する
    if not isinstance(raw_list, list) or not all(isinstance(item, dict) for item in raw_list):
        msg = (
            f"unexpected response type: expected list[dict], "
            f"got {type(raw_list).__name__}"
        )
        print(f"  [エラー] {msg}")
        save_error(msg)
        return

    print(f"  取得件数: {len(raw_list)}")
    _save_json(provider_dir / "raw.json", raw_list)

    # API側がlimitを無視して多く返す場合があるため、正規化前にスライスする
    truncated = raw_list[:limit]
    if len(raw_list) > limit:
        print(f"  正規化件数: {limit}件 (API取得: {len(raw_list)}件)")

    # normalize 中の例外も捕捉してプロバイダー全体が落ちないようにする
    try:
        normalized = [spec.normalize(raw).to_dict() for raw in truncated]
    except Exception as e:
        msg = f"normalize error: {e}"
        print(f"  [エラー] {_sanitize_str(msg)}")
        save_error(msg)
        return

    _save_json(provider_dir / "normalized.json", normalized)


def main() -> None:
    provider_names = [spec.name for spec in _REGISTRY]

    parser = argparse.ArgumentParser(description="X検索結果を複数のAPIで比較する")
    parser.add_argument("query", help="検索語")
    parser.add_argument("--limit", type=int, default=50, help="取得件数 (デフォルト: 50)")
    parser.add_argument(
        "--provider",
        choices=provider_names + ["both"],
        default="both",
        help="使用するプロバイダー (デフォルト: both)",
    )
    parser.add_argument(
        "--query-type",
        choices=["Top", "Latest"],
        default="Latest",
        help="検索の並び順 (デフォルト: Latest)",
    )
    args = parser.parse_args()

    output_dir = _make_output_dir(args.query, args.query_type)
    print(f"出力先: {output_dir}")

    for spec in _REGISTRY:
        if args.provider not in (spec.name, "both"):
            continue
        api_key = os.getenv(spec.env_key, "")
        if not api_key:
            print(f"[警告] {spec.env_key} が未設定です。{spec.name} をスキップします。")
            continue
        _run_provider(spec, args.query, args.limit, api_key, output_dir, args.query_type)

    print("\n完了。")


if __name__ == "__main__":
    main()
