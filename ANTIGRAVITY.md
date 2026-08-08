# Antigravity CLI Instructions: Stock Fetcher Project

本ドキュメントは、Antigravity CLI をはじめとする AI エージェントが本リポジトリ内でコード生成・改修を行う際の大原則および開発規約を定義する。

---

## 🎯 プロジェクトの核心原則

1. **ターゲット層は非IT層**: エンドユーザーにコマンドライン操作や環境構築を求めてはならない。最終アウトプットは必ず PyInstaller による単一実行ファイルとする。
2. **依存関係管理は `uv` を徹底**: パッケージ追加や実行命令は `pip` や `poetry` ではなく、すべて `uv`（`uv add`, `uv run` 等）を使用すること。
3. **エラーで落ちない堅牢性**: API通信エラーや特定指標の取得漏れ（`None` 返却）が発生しても、プログラム全体を止めずに `N/A` で補完して処理を継続すること。

---

## 🧱 機能仕様および設計要件

### 1. データ取得と設定保持 (`user_config.json`)

ユーザーの選択状態は、アプリ終了時および変更時に自動保存し、次回起動時に復元すること。保存対象は以下の2点：

- **選択中の銘柄コード (`selected_tickers`)**
- **選択中の出力項目キー (`selected_fields`)**

### 2. 出力項目定義 (選択可能項目)

データ取得モジュール（`app/fetcher.py`）では、以下のフィールドキーを定義し、UI側でチェックONになっている項目のみをCSVへ出力すること。

| フィールドキー | 表示名 | データ参照・計算方法 |
| --- | --- | --- |
| `date` | 取得日時 | システム現在時刻 (`YYYY-MM-DD HH:mm:ss`) |
| `ticker` | 銘柄コード | ティッカーシンボル |
| `company_name` | 企業名 | マスターまたは `info['longName']` |
| `price` | 株価 | `info['currentPrice']` または `info['regularMarketPrice']` |
| `per` | PER | `info['trailingPE']` または `info['forwardPE']` |
| `pbr` | PBR | `info['priceToBook']` |
| `dividend_yield` | 配当利回り(%) | `info['dividendYield'] * 100` |
| `roe` | ROE(%) | `info['returnOnEquity'] * 100` |
| `revenue_growth` | 売上高成長率(%) | `info['revenueGrowth'] * 100` |
| `operating_margins` | 営業利益率(%) | `info['operatingMargins'] * 100` |
| `equity_ratio` | 自己資本比率(%) | `Total Stockholder Equity / Total Assets * 100` |

### 3. アプリ起動時処理 (`app/updater.py`)

- バックグラウンドで最新の銘柄一覧（日本株等）を取得し、`master_tickers.json` を差分更新すること。
- 通信エラーが発生した場合は例外をキャッチし、ローカルに保持されているキャッシュファイルをそのまま利用して起動を継続させること。

---

## 💻 開発・コーディング規約

- **Python**: 型ヒント（Type Hints）を明記し、非同期処理（`async/await`）が有効な部分は FastAPI の設計に沿って記述すること。
- **JS / UI**: ライブラリに過度に依存せず、Vanilla JS + Tailwind CSS で軽量かつ高速に動作させること。
