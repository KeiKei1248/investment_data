import os
import sys
import json
import io
import requests
import urllib.parse
from bs4 import BeautifulSoup
import pandas as pd
import asyncio
import ctypes
from typing import List, Dict

JPX_PAGE_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
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

def hide_file(filepath: str):
    """Windows環境でファイルを隠しファイル化する"""
    if sys.platform.startswith("win"):
        try:
            # 2 は FILE_ATTRIBUTE_HIDDEN
            ctypes.windll.kernel32.SetFileAttributesW(filepath, 2)
        except Exception as e:
            print(f"Failed to hide file {filepath}: {e}")

def _fetch_jpx_tickers() -> List[Dict[str, str]]:
    """JPXの公式サイトから上場銘柄一覧Excelの最新URLをスクレイピングしてダウンロード・解析する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 1. 統計ページを取得してExcelの直リンクを探索
    page_resp = requests.get(JPX_PAGE_URL, headers=headers, timeout=15)
    page_resp.raise_for_status()
    
    soup = BeautifulSoup(page_resp.text, 'html.parser')
    excel_url = None
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'data_j.xls' in href or 'data_j.xlsx' in href:
            excel_url = urllib.parse.urljoin(JPX_PAGE_URL, href)
            break
            
    if not excel_url:
        raise ValueError("JPX Excel link not found on the page.")
        
    print(f"Downloading JPX Excel from dynamic URL: {excel_url}")
    
    # 2. ダウンロード
    resp = requests.get(excel_url, headers=headers, timeout=15)
    resp.raise_for_status()
    
    # 3. メモリ上のExcelを読み込み（xlrdを使用）
    df = pd.read_excel(io.BytesIO(resp.content), engine="xlrd")
    
    # 列名のクリーニング
    df.columns = [str(c).strip() for c in df.columns]
    
    # インデックスで列を指定（1:コード, 2:銘柄名）
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
        # コードが4桁の数字であることを確認 (ETFや普通株式などをすべて包含)
        if code_str.isdigit() and len(code_str) == 4:
            ticker = f"{code_str}.T"
            tickers.append({"ticker": ticker, "name": str(name_val).strip()})
            
    return tickers

async def update_master_tickers() -> List[Dict[str, str]]:
    """起動時にマスター銘柄情報を非同期で更新する。失敗時はローカルキャッシュを使用する。"""
    os.makedirs("data", exist_ok=True)
    # dataディレクトリ自体も隠しフォルダにする
    hide_file("data")
    
    try:
        tickers = await asyncio.to_thread(_fetch_jpx_tickers)
        
        if tickers:
            with open(MASTER_FILE, "w", encoding="utf-8") as f:
                json.dump(tickers, f, ensure_ascii=False, indent=2)
            # 作成したファイルを隠しファイル化
            hide_file(MASTER_FILE)
            print(f"master_tickers.json updated successfully with {len(tickers)} tickers.")
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
    hide_file(MASTER_FILE)
    return DEFAULT_TICKERS
