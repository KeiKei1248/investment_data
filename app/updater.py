import os
import json
import requests
import pandas as pd
import asyncio
from typing import List, Dict

JPX_URL = "https://www.jpx.co.jp/markets/statistics-metadata/market-categories/tvdivq0000001vg2-att/data_j.xls"
MASTER_FILE = "data/master_tickers.json"

DEFAULT_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc."},
    {"ticker": "MSFT", "name": "Microsoft Corp."},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "AMZN", "name": "Amazon.com Inc."},
    {"ticker": "NVDA", "name": "NVIDIA Corp."},
    {"ticker": "7203.T", "name": "トヨタ自動車"},
    {"ticker": "9984.T", "name": "ソフトバンクグループ"},
    {"ticker": "6758.T", "name": "ソニーグループ"},
    {"ticker": "6861.T", "name": "キーエンス"},
    {"ticker": "7974.T", "name": "任天堂"},
    {"ticker": "6501.T", "name": "日立製作所"},
    {"ticker": "8058.T", "name": "三菱商事"}
]

def _fetch_jpx_tickers() -> List[Dict[str, str]]:
    """JPXの公式サイトから上場銘柄一覧Excelをダウンロードして解析する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    # ダウンロード
    resp = requests.get(JPX_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    
    # メモリ上のExcelを読み込み
    df = pd.read_excel(resp.content)
    
    # 列名のクリーニング
    df.columns = [str(c).strip() for c in df.columns]
    
    code_col = None
    name_col = None
    for col in df.columns:
        if "コード" in col:
            code_col = col
        elif "銘柄名" in col:
            name_col = col
            
    if not code_col or not name_col:
        # 見つからない場合はインデックスで推測
        code_col = df.columns[1]
        name_col = df.columns[2]
        
    tickers = []
    
    # 米国株などのデフォルト銘柄を先頭に追加しておく
    for item in DEFAULT_TICKERS:
        if not item["ticker"].endswith(".T"):
            tickers.append(item)
            
    # JPXの銘柄をパース
    for _, row in df.iterrows():
        code_val = row[code_col]
        name_val = row[name_col]
        if pd.isna(code_val) or pd.isna(name_val):
            continue
            
        code_str = str(code_val).strip()
        # コードが4桁の数字であることを確認
        if code_str.isdigit():
            ticker = f"{code_str}.T"
            tickers.append({"ticker": ticker, "name": str(name_val).strip()})
            
    return tickers

async def update_master_tickers() -> List[Dict[str, str]]:
    """起動時にマスター銘柄情報を非同期で更新する。失敗時はローカルキャッシュを使用する。"""
    os.makedirs("data", exist_ok=True)
    try:
        # asyncio.to_thread を用いてブロッキング処理を非同期化
        tickers = await asyncio.to_thread(_fetch_jpx_tickers)
        
        if tickers:
            with open(MASTER_FILE, "w", encoding="utf-8") as f:
                json.dump(tickers, f, ensure_ascii=False, indent=2)
            print("master_tickers.json has been updated successfully.")
            return tickers
    except Exception as e:
        print(f"Failed to update master tickers from JPX: {e}. Using cached or default data.")
        
    # エラー時は既存のキャッシュファイルを確認
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # キャッシュも読み込めない場合はデフォルト値を書き出して返す
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_TICKERS, f, ensure_ascii=False, indent=2)
    return DEFAULT_TICKERS
