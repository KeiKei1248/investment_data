import os
import sys
import json
import io
import requests
import pandas as pd
import asyncio
import ctypes
from typing import List, Dict

JPX_EXCEL_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
MASTER_FILE = "data/master_tickers.json"

DEFAULT_TICKERS = [
    {"date": "20260731", "ticker": "7203.T", "name": "トヨタ自動車", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "9984.T", "name": "ソフトバンクグループ", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6758.T", "name": "ソニーグループ", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6861.T", "name": "キーエンス", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "7974.T", "name": "任天堂", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "6501.T", "name": "日立製作所", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "8058.T", "name": "三菱商事", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "9983.T", "name": "ファーストリテイリング", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "8306.T", "name": "三菱UFJフィナンシャル・グループ", "segment": "プライム（内国株式）"},
    {"date": "20260731", "ticker": "4502.T", "name": "武田薬品工業", "segment": "プライム（内国株式）"}
]

# 更新状態の追跡
update_status = "idle" # idle, updating, completed, error

def hide_file(filepath: str):
    """Windows環境でファイルを隠しファイル化する"""
    if sys.platform.startswith("win"):
        try:
            # 2 は FILE_ATTRIBUTE_HIDDEN
            ctypes.windll.kernel32.SetFileAttributesW(filepath, 2)
        except Exception as e:
            print(f"Failed to hide file {filepath}: {e}")

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
                "segment": str(market_val).strip() if not pd.isna(market_val) else "その他"
            })
            
    return tickers

def load_cached_tickers() -> List[Dict[str, str]]:
    """ローカルにキャッシュされた日本株銘柄データをロードする。無ければデフォルト値を返す。"""
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # キャッシュが無ければデフォルトリストを即座に作成して返す
    os.makedirs("data", exist_ok=True)
    hide_file("data")
    try:
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TICKERS, f, ensure_ascii=False, indent=2)
        hide_file(MASTER_FILE)
    except Exception:
        pass
    return DEFAULT_TICKERS

async def update_master_tickers_in_background():
    """バックグラウンドでJPX上場銘柄マスターを同期する"""
    global update_status
    if update_status == "updating":
        return
        
    update_status = "updating"
    
    try:
        tickers = await asyncio.to_thread(_fetch_jpx_tickers)
        if tickers:
            with open(MASTER_FILE, "w", encoding="utf-8") as f:
                json.dump(tickers, f, ensure_ascii=False, indent=2)
            hide_file(MASTER_FILE)
            update_status = "completed"
            print(f"Background JPX sync complete: {len(tickers)} tickers synced.")
    except Exception as e:
        update_status = "error"
        print(f"Failed background JPX sync: {e}")
