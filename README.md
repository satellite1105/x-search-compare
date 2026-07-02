# x-search-compare

twitterapi.io と GetXAPI の X 検索結果を同じ形式に正規化して比較するツール。

## 現状

twitterapi.io / GetXAPI とも Advanced Search API の疎通・正規化を確認済みです。

- エンドポイントURL・認証方式・リクエストパラメータ・レスポンスのJSONキー構造は、実際のAPIレスポンスで動作確認済みです。
- **GetXAPI は `queryType` ではなく `product` パラメータで Top/Latest を指定する**（公式仕様確認済み）。twitterapi.io は `queryType` を使う。両者はパラメータ名が異なるため、`compare_search.py` の `--query-type` は共通の入力値として受け取り、各プロバイダー内部で対応するパラメータ名（`queryType` または `product`）に変換して送信する。
- 過去（2026-07-01時点）の比較結果は、GetXAPI側で `queryType` パラメータが送信されていた（`product` ではなく）ため、GetXAPI側のTop/Latest指定が効いていなかった可能性がある。修正後に再検証済み（詳細は「現時点の比較結果」セクション参照）。
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

> **注意**: `--query-type` は `Top` / `Latest` の2値を両プロバイダー共通の入力として受け取るが、実際にAPIへ渡すパラメータ名はプロバイダーごとに異なる。
> - twitterapi.io: `queryType` パラメータで指定
> - GetXAPI: `product` パラメータで指定（`queryType` ではない。公式仕様確認済み）
>
> 各パラメータの指定値・実際の挙動の細部（`Top`/`Latest` 以外の値の有無など）は公式ドキュメントで完全には確認できていない箇所がある（`x_search/providers/` の `# TODO` 参照）。

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

### 2026-07-02 再検証（GetXAPI を `product` パラメータに修正後）

GetXAPI が `queryType` ではなく `product` パラメータを使う仕様と判明したため修正し、`--limit 20 --provider both` で以下4パターンを再実行した（同一ツイート率 = twitterapi.io と GetXAPI の正規化後IDの Jaccard 一致率）。

| クエリ | queryType/product | 同一ツイート率（新） | 同一ツイート率（旧・修正前） |
|---|---|---|---|
| AI 副業 | Top | 37.9% | 2.6% |
| AI 副業 | Latest | 100.0% | 100.0% |
| Claude Code | Top | 18.2% | 2.6% |
| Claude Code | Latest | 100.0% | 100.0% |

- 4パターンとも `error.json` は生成されず、両APIとも疎通・正規化に成功した。
- `Latest` は修正前後とも同一ツイート率100%で変化なし。
- `Top` は修正前は2.6%と非常に低かったが、修正後は18.2%〜37.9%に上昇した。これは、修正前はGetXAPI側で `queryType` パラメータが送信されており実際には `product` が指定されずGetXAPI側のTop/Latestが正しく切り替わっていなかった可能性を示唆する結果である。
- ただし修正後も `Top` の一致率は `Latest` と比べて大きく低く、両APIの「人気順」の定義・ランキングアルゴリズム自体に差がある可能性が高い。

> 上記は限定的なクエリ・件数（`--limit 20`）での検証結果であり、継続的な検証が必要。旧所見（「Latestはほぼ一致、Topは大きく異なる」という傾向自体）は今回も再現されたが、旧データの `Top` の数値（一致率数%）はGetXAPI側のパラメータ不備によるものだった可能性があるため、旧データの絶対値は参考値として扱うこと。

### 旧所見（2026-07-01、`queryType` 修正前・参考情報）

- twitterapi.io / GetXAPI とも Advanced Search API の疎通に成功している。
- `queryType=Latest` では、両APIの結果はほぼ一致する（同一ツイート率はおおむね100%）。
- `queryType=Top` では、両APIの結果は大きく異なる（同一ツイート率が数%程度まで低下するケースを確認）。
- GetXAPIは料金が安いが、Top検索の解釈差には注意が必要。
- 実用上、Latest中心の運用であればGetXAPIが有力候補。
- Top検索（人気順）を重視する場合はtwitterapi.ioも候補となる。

> **注意**: 上記の旧所見はGetXAPI側で `queryType` パラメータが送信されていた（`product` ではなく）時点のものであり、GetXAPI側のTop/Latest指定が実際には効いていなかった可能性がある。修正後の再検証結果（上記セクション）を優先すること。

## 開発メモ（TODOについて）

各プロバイダーの実装（`x_search/providers/`）には `# TODO` コメントがある。
主な残課題:

- Top/Latest（`queryType` / `product`）の解釈がAPI間で一致しているか（要追加検証。詳細は「現時点の比較結果」参照）
- GetXAPI の `cursor` によるページネーションは未実装（1回のAPI呼び出しにつき最大20件/pageのみ取得）
- twitterapi.io のページネーションパラメータ名・両APIのレート制限の仕様（公式ドキュメントで未確認）
- レスポンスのエッジケース（フィールド欠損時の挙動など）
