# x-search-compare

twitterapi.io と GetXAPI の X 検索結果を同じ形式に正規化して比較するツール。

## 現状

twitterapi.io / GetXAPI とも Advanced Search API の疎通・正規化を確認済みです。

- エンドポイントURL・認証方式・リクエストパラメータ・レスポンスのJSONキー構造は、実際のAPIレスポンスで動作確認済みです。
- 残課題は `queryType=Top` の解釈がAPI間で異なる可能性がある点で、要追加検証です（詳細は「現時点の比較結果」セクション参照）。
- その他の細部（ページネーション・レート制限の仕様など）は末尾の「開発メモ」セクションを参照してください。

## セットアップ

### 1. リポジトリをクローン後、仮想環境を作成

```bash
cd x-search-compare
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. APIキーの設定

`.env.example` をコピーして `.env` を作成し、各サービスのAPIキーを入力する。

```bash
cp .env.example .env
```

`.env` を編集:

```
TWITTERAPI_IO_KEY=取得したAPIキーをここに貼る
GETXAPI_KEY=取得したAPIキーをここに貼る
```

#### APIキーの取得方法

- **twitterapi.io**: https://twitterapi.io にアクセスしてアカウント登録後、APIキーを発行
- **GetXAPI**: https://getxapi.com にアクセスしてアカウント登録後、APIキーを発行

> **注意**: `.env` はGitにコミットされません。絶対に公開しないでください。

## 使い方

### 基本実行（両方のAPIを比較）

```bash
python3 compare_search.py "Claude AI"
```

### 件数を指定

```bash
python3 compare_search.py "Claude AI" --limit 100
```

> **注意（twitterapi.io）**: twitterapi.io の Advanced Search API は1リクエストで最大20件を返す仕様です。`--limit` はAPI呼び出し件数の指定ではなく、保存・正規化する件数の上限として扱われます。`raw.json` にはAPIレスポンス全件、`normalized.json` には `--limit` 件数に切り詰めた結果が保存されます。

### プロバイダーを指定

```bash
# twitterapi.io のみ
python3 compare_search.py "Claude AI" --provider twitterapi_io

# GetXAPI のみ
python3 compare_search.py "Claude AI" --provider getxapi

# 両方（デフォルト）
python3 compare_search.py "Claude AI" --provider both
```

### 検索の並び順を指定 (queryType)

```bash
# 人気順 (Top)
python3 compare_search.py "Claude AI" --query-type Top

# 新着順 (Latest, デフォルト)
python3 compare_search.py "Claude AI" --query-type Latest
```

> **注意**: `queryType` に指定できる値・実際の挙動は各プロバイダーの公式ドキュメントで未確認（`x_search/providers/` の `# TODO` 参照）。現時点では `Top` / `Latest` の2値を両プロバイダーに共通のパラメータとして渡している。

## 出力

検索を実行すると `data/` 以下にタイムスタンプ付きのディレクトリが作成される。

```
data/
└── 20240101_120000_123456_Claude_AI_Latest/
    ├── twitterapi_io/
    │   ├── raw.json         # APIレスポンスをそのまま保存
    │   └── normalized.json  # 正規化後のデータ
    └── getxapi/
        ├── raw.json
        └── normalized.json
```

ディレクトリ名の末尾には `--query-type` の値（`Top` または `Latest`）が付与される。

エラーが発生した場合は `error.json` が保存され、プログラムは継続する。

### normalized.json のフィールド

| フィールド | 説明 |
|-----------|------|
| `id` | ツイートID |
| `text` | 本文 |
| `url` | ツイートURL |
| `author_username` | 投稿者のユーザー名（@なし） |
| `author_name` | 投稿者の表示名 |
| `created_at` | 投稿日時（ISO 8601） |
| `like_count` | いいね数 |
| `repost_count` | リポスト数 |
| `reply_count` | リプライ数 |
| `view_count` | 閲覧数 |
| `source` | データソース（`twitterapi_io` or `getxapi`） |

## 現時点の比較結果

複数クエリ・`--query-type Top/Latest` での実行結果に基づく現時点の所見:

- twitterapi.io / GetXAPI とも Advanced Search API の疎通に成功している。
- `queryType=Latest` では、両APIの結果はほぼ一致する（同一ツイート率はおおむね100%）。
- `queryType=Top` では、両APIの結果は大きく異なる（同一ツイート率が数%程度まで低下するケースを確認）。
- GetXAPIは料金が安いが、Top検索の解釈差には注意が必要。
- 実用上、Latest中心の運用であればGetXAPIが有力候補。
- Top検索（人気順）を重視する場合はtwitterapi.ioも候補となる。

> 上記は限定的なクエリ・件数での検証結果であり、継続的な検証が必要。`queryType=Top` の解釈差の原因（API仕様差なのか実装上の問題か）は未特定。

## 開発メモ（TODOについて）

各プロバイダーの実装（`x_search/providers/`）には `# TODO` コメントがある。
主な残課題:

- `queryType=Top` の解釈がAPI間で一致しているか（要追加検証。詳細は「現時点の比較結果」参照）
- ページネーションパラメータ名・レート制限の仕様（公式ドキュメントで未確認）
- レスポンスのエッジケース（フィールド欠損時の挙動など）
