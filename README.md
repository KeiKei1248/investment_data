# 📈 長期投資向け銘柄情報自動取得ツール (Stock Fetcher)

指定した企業（日本株・米国株等）の長期投資に必要な主要財務・株価指標をYahoo Financeから自動取得し、ローカル環境でCSV出力するデスクトップアプリケーションです。
IT知識がないユーザーでも、ダブルクリックだけで直感的に操作できるように設計されています。

---

## ✨ 主な特徴

- **1ファイルで完結**: PythonやDockerの環境構築が不要な単一実行ファイル（`.exe` / `.app`）。
- **洗練されたWeb UI**: HTML/JS/Tailwind CSSによる直感的な操作画面（検索・フィルタリング対応）。
- **銘柄マスター自動更新**: アプリ起動時に最新の企業リスト（東証上場銘柄等）をバックグラウンドで自動同期。
- **柔軟なカスタマイズ**:
  - 対象銘柄の選択・保持（次回起動時にも前回のチェック状態を完全復元）。
  - **出力項目の個別チェック選択**（株価、PER、PBR、ROE、配当利回りなど必要な項目だけを抽出可能）。
- **uv による高速・厳密な開発環境管理**: 開発時は `uv` と `uv.lock` により再現性の高い環境を提供。

---

## 🛠 技術スタック

- **パッケージ管理**: `uv`
- **バックエンド**: Python 3.10+, FastAPI, Uvicorn
- **デスクトップ化**: PyInstaller, PyWebView
- **フロントエンド**: HTML5, Vanilla JS, Tailwind CSS
- **データ取得**: `yfinance`, `pandas`

---

## 🚀 開発・ビルド手順（開発者向け）

### 1. 依存関係のセットアップ (`uv` の使用)

```bash
# クローンと依存関係のインストール
git clone [https://github.com/your-username/stock-fetcher.git](https://github.com/your-username/stock-fetcher.git)
cd stock-fetcher

# uvによる環境同期
uv sync
```

### 2. ローカル開発サーバーの起動

```bash
uv run python -m app.main
```

### 3. 単一実行ファイル化（ビルド）

```bash
uv run python build.py
```

ビルド完了後、dist/ ディレクトリ内に実行ファイル（.exe または .app）が生成されます。

## 📁 ディレクトリ構成

```
INVESTMENT_DATA/
├── pyproject.toml         # uv 管理の依存関係定義
├── uv.lock                # バージョン固定用ロックファイル
├── build.py               # PyInstaller ビルドスクリプト
├── app/
│   ├── main.py            # FastAPI エントリーポイント & PyWebView 起動
│   ├── updater.py         # 銘柄マスター自動更新モジュール
│   ├── fetcher.py         # yfinance データ取得モジュール
│   ├── static/            # JS / CSS アセット
│   └── templates/         # HTML テンプレート
└── data/
    ├── master_tickers.json # 企業マスター（起動時自動更新）
    ├── user_config.json   # 前回選択状態（銘柄・出力項目）の保持
    └── output/            # 出力先CSVデフォルトフォルダ
```
