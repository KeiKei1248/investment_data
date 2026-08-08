import sys

import PyInstaller.__main__


def build():
    # 静的ファイルのパス区切りをOSに合わせて調整
    # Windows: セミコロン(;), macOS/Linux: コロン(:)
    sep = ";" if sys.platform.startswith("win") else ":"

    # アセットフォルダの同梱設定
    # format: <ソースパス><区切り文字><宛先パス>
    add_data_templates = f"app/templates{sep}app/templates"
    add_data_static = f"app/static{sep}app/static"

    opts = [
        "app/main.py",  # エントリーポイント
        "--onefile",  # 単一の実行ファイルにまとめる
        "--name=StockFetcher",  # 実行ファイルの名称
        f"--add-data={add_data_templates}",
        f"--add-data={add_data_static}",
        "--clean",  # ビルド前にビルドキャッシュをクリア
        "--noconsole",  # 起動時の黒いコマンドプロンプト(CUI)を非表示にする
    ]

    print("==========================================")
    print("PyInstaller による Stock Fetcher のビルドを開始します...")
    print(f"ビルドオプション: {opts}")
    print("==========================================")

    try:
        PyInstaller.__main__.run(opts)
        print(
            "[SUCCESS] ビルドが正常に完了しました。dist/ ディレクトリを確認してください。"
        )
    except Exception as e:
        print(f"[ERROR] ビルド中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
