"""
ローカル設定ファイル (config.json) の読み書きロジック (バックエンド部分)
"""

import os
import json


def load_config(filepath: str) -> dict:
    """設定ファイルを読み込み辞書を返す。存在しない場合や失敗時は空辞書を返す"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(filepath: str, data: dict) -> bool:
    """設定データを JSON 形式で保存する"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
