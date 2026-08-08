import sys
import os
import ctypes

import PyInstaller.__main__


def clear_attributes(filepath):
    """Windows環境でファイルの隠し属性や読み取り専用属性を解除する"""
    if sys.platform.startswith("win") and os.path.exists(filepath):
        try:
            # 128 は FILE_ATTRIBUTE_NORMAL
            ctypes.windll.kernel32.SetFileAttributesW(filepath, 128)
            print(f"Cleared file attributes for {filepath}")
        except Exception as e:
            print(f"Failed to clear attributes for {filepath}: {e}")


def build():
    # 静的ファイルのパス区切りをOSに合わせて調整
    # Windows: セミコロン(;), macOS/Linux: コロン(:)
    sep = ";" if sys.platform.startswith("win") else ":"

    # アセットフォルダの同梱設定
    # format: <ソースパス><区切り文字><宛先パス>
    add_data_templates = f"app/templates{sep}app/templates"
    add_data_static = f"app/static{sep}app/static"

    target_exe = os.path.join("dist", "StockFetcher.exe")
    clear_attributes(target_exe)

    opts = [
        "app/main.py",  # エントリーポイント
        "--onefile",  # 単一の実行ファイルにまとめる
        "--name=StockFetcher",  # 実行ファイルの名称
        f"--add-data={add_data_templates}",
        f"--add-data={add_data_static}",
        "--icon=app/static/app.ico",  # 実行ファイルのアイコンを設定
        "--clean",  # ビルド前にビルドキャッシュをクリア
        "--noconsole",  # 起動時の黒いコマンドプロンプト(CUI)を非表示にする
    ]

    print("==========================================")
    print("Starting PyInstaller build for Stock Fetcher...")
    print(f"Build options: {opts}")
    print("==========================================")

    try:
        PyInstaller.__main__.run(opts)
        print(
            "[SUCCESS] Build completed successfully. Check the dist/ directory."
        )
    except Exception as e:
        print(f"[ERROR] Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
