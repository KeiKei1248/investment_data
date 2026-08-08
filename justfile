# Windows PowerShell をデフォルトシェルとして指定
set shell := ["powershell", "-Command"]

# デフォルト動作（just とだけ打った場合に初期セットアップからビルドまで全自動実行）
default: 
    @just --list

# 初期セットアップからビルドまで一括実行
all: setup build

# 依存関係のセットアップ・同期
setup:
    uv sync

# ローカル開発サーバーの起動
dev:
    uv run python -m app.main

# PyInstaller による爆速起動向けフォルダ形式ビルド (--onedir)
build:
    uv run python build.py

# ビルド成果物やキャッシュのクリーンアップ
clean:
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, *.spec

# 銘柄マスターデータをJPXから取得して手動更新する
update-master:
    uv run python -m app.updater