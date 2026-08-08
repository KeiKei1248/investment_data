import os
import sys
import json
import io
import requests
import pandas as pd
import asyncio
import ctypes
from typing import List, Dict, Callable, Any

# 実行ファイルの位置（またはカレントディレクトリ）を特定する（パス解決の絶対化）
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
else:
    # updater.py は app/ ディレクトリにあるので、1つ上の階層をプロジェクトディレクトリとする
    EXE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MASTER_FILE = os.path.join(EXE_DIR, "data", "master_tickers.json")
CONFIG_PATH = os.path.join(EXE_DIR, "data", "user_config.json")

JPX_EXCEL_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"

DEFAULT_TICKERS = [
    {"date": "20260731", "ticker": "7203.T", "name": "トヨタ自動車", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "9984.T", "name": "ソフトバンクグループ", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6758.T", "name": "ソニーグループ", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6861.T", "name": "キーエンス", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "7974.T", "name": "任天堂", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6501.T", "name": "日立製作所", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "8058.T", "name": "三菱商事", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "9983.T", "name": "ファーストリテイリング", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "8306.T", "name": "三菱UFJフィナンシャル・グループ", "category": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "4502.T", "name": "武田薬品工業", "category": "プライム（内国株式）"}
]

# 更新状態の追跡
update_status = "idle" # idle, updating, completed, error

def get_update_status() -> str:
    """現在の同期ステータスを取得する"""
    global update_status
    return update_status

def set_file_attributes(filepath: str, hidden: bool):
    """Windows環境でファイルの隠し属性を設定または解除する"""
    if sys.platform.startswith("win"):
        try:
            # 2 は FILE_ATTRIBUTE_HIDDEN, 128 (0x80) は FILE_ATTRIBUTE_NORMAL
            attr = 2 if hidden else 128
            ctypes.windll.kernel32.SetFileAttributesW(filepath, attr)
        except Exception as e:
            print(f"Failed to set file attributes for {filepath}: {e}")

def hide_file(filepath: str):
    """ファイルを隠しファイル化する"""
    set_file_attributes(filepath, True)

def show_file(filepath: str):
    """ファイルの隠し属性を解除する（書き込み権限エラー回避用）"""
    set_file_attributes(filepath, False)

def _fetch_jpx_tickers() -> List[Dict[str, str]]:
    """JPXの公式サイトから上場銘柄一覧Excelを直接ダウンロードし、4項目を抽出する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Downloading JPX Excel: {JPX_EXCEL_URL}")
    resp = requests.get(JPX_EXCEL_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    
    # メモリ上のExcelを読み込み（xlrdを使用）
    df = pd.read_excel(io.BytesIO(resp.content), engine="xlrd")
    df.columns = [str(c).strip() for c in df.columns]
    
    # 列を特定 (0: 日付, 1: コード, 2: 銘柄名, 3: 市場・商品区分)
    date_col = df.columns[0]
    code_col = df.columns[1]
    name_col = df.columns[2]
    market_col = df.columns[3]
        
    tickers = []
    for _, row in df.iterrows():
        date_val = row[date_col]
        code_val = row[code_col]
        name_val = row[name_col]
        market_val = row[market_col]
        
        if pd.isna(code_val) or pd.isna(name_val):
            continue
            
        code_str = str(code_val).strip()
        # 銘柄コードが4桁であること (普通株式、主要ETFなどを抽出)
        if code_str.isdigit() and len(code_str) == 4:
            tickers.append({
                "date": str(date_val).strip() if not pd.isna(date_val) else "",
                "ticker": f"{code_str}.T",
                "name": str(name_val).strip(),
                "category": str(market_val).strip() if not pd.isna(market_val) else "その他"
            })
            
    return tickers

def load_cached_tickers() -> Dict[str, List[Dict[str, str]]]:
    """ローカルにキャッシュされた日本株銘柄データをロードする。無ければデフォルト値を返す。"""
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 古い形式（リスト型）だった場合の移行互換処理
                if isinstance(data, list):
                    data = {"japan": data}
                
                # segment キーを category に変換する互換処理
                if "japan" in data:
                    updated = False
                    for item in data["japan"]:
                        if "segment" in item and "category" not in item:
                            item["category"] = item.pop("segment")
                            updated = True
                    if updated:
                        show_file(MASTER_FILE)
                        with open(MASTER_FILE, "w", encoding="utf-8") as wf:
                            json.dump(data, wf, ensure_ascii=False, indent=2)
                        hide_file(MASTER_FILE)
                return data
        except Exception:
            pass
            
    # キャッシュが無ければデフォルトリストを即座に作成して返す
    os.makedirs(os.path.dirname(MASTER_FILE), exist_ok=True)
    hide_file(os.path.dirname(MASTER_FILE))
    default_data = {"japan": DEFAULT_TICKERS}
    try:
        show_file(MASTER_FILE)
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        hide_file(MASTER_FILE)
    except Exception:
        pass
    return default_data

async def update_master_tickers_in_background(on_complete: Callable[[], Any] = None):
    """バックグラウンドでJPX上場銘柄マスターを同期する"""
    global update_status
    if update_status == "updating":
        return
        
    update_status = "updating"
    
    try:
        tickers = await asyncio.to_thread(_fetch_jpx_tickers)
        if tickers:
            data = {"japan": tickers}
            os.makedirs(os.path.dirname(MASTER_FILE), exist_ok=True)
            show_file(MASTER_FILE)
            with open(MASTER_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            hide_file(MASTER_FILE)
            update_status = "completed"
            print(f"Background JPX sync complete: {len(tickers)} tickers synced.")
            if on_complete:
                if asyncio.iscoroutinefunction(on_complete):
                    await on_complete()
                else:
                    on_complete()
    except Exception as e:
        update_status = "error"
        print(f"Failed background JPX sync: {e}")


if __name__ == "__main__":
    from datetime import datetime
    print("Updating JPX stock master tickers...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def on_complete():
            cfg = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            
            cfg["master_last_updated"] = datetime.now().strftime("%Y-%m-%d")
            if "selected_category" not in cfg:
                cfg["selected_category"] = "プライム（内国株式）"
            if "selected_tickers" not in cfg:
                cfg["selected_tickers"] = ["7203.T"]
            if "selected_fields" not in cfg:
                cfg["selected_fields"] = [
                    "date", "ticker", "company_name", "price", "per", "pbr", "dividend_yield", "equity_ratio"
                ]
            if "output_path" not in cfg:
                cfg["output_path"] = "stock_data.csv"
                
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            show_file(CONFIG_PATH)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            hide_file(CONFIG_PATH)
            print("Successfully updated user_config.json with master_last_updated.")

        loop.run_until_complete(update_master_tickers_in_background(on_complete))
        print("Stock master tickers update finished.")
    except Exception as e:
        print(f"Error: {e}")

