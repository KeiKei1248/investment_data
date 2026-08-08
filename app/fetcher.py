import os
import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Any, Callable

# フィールド定義とフォーマット関数のマップ
# ANTIGRAVITY.md の仕様に厳密に従う
FIELD_METADATA = {
    "date": {"display": "取得日時", "fmt": lambda x: str(x)},
    "ticker": {"display": "銘柄コード", "fmt": lambda x: str(x)},
    "company_name": {"display": "企業名", "fmt": lambda x: str(x) if x else "N/A"},
    "price": {"display": "株価", "fmt": lambda x: f"{float(x):,.1f}" if x is not None else "N/A"},
    "per": {"display": "PER", "fmt": lambda x: f"{float(x):.2f}" if x is not None else "N/A"},
    "pbr": {"display": "PBR", "fmt": lambda x: f"{float(x):.2f}" if x is not None else "N/A"},
    "dividend_yield": {"display": "配当利回り(%)", "fmt": lambda x: f"{float(x):.2f}%" if x is not None else "N/A"},
    "roe": {"display": "ROE(%)", "fmt": lambda x: f"{float(x):.2f}%" if x is not None else "N/A"},
    "revenue_growth": {"display": "売上高成長率(%)", "fmt": lambda x: f"{float(x):.2f}%" if x is not None else "N/A"},
    "operating_margins": {"display": "営業利益率(%)", "fmt": lambda x: f"{float(x):.2f}%" if x is not None else "N/A"},
    "equity_ratio": {"display": "自己資本比率(%)", "fmt": lambda x: f"{float(x):.2f}%" if x is not None else "N/A"},
}

def _get_equity_ratio(ticker_obj: yf.Ticker) -> float | None:
    """バランスシートから自己資本比率 (Total Stockholder Equity / Total Assets * 100) を計算する"""
    try:
        # yfinanceの balance_sheet (または quarterly_balance_sheet) を取得
        bs = ticker_obj.balance_sheet
        if bs is None or bs.empty:
            bs = ticker_obj.quarterly_balance_sheet
        if bs is None or bs.empty:
            return None
        
        # 行名のクリーニングと小文字化
        idx_lower = [str(x).lower().replace(" ", "").replace("_", "") for x in bs.index]
        
        equity_val = None
        assets_val = None
        
        # Total Stockholder Equity の検索
        target_equity_keys = ["totalstockholderequity", "stockholdersequity", "totalequity"]
        for k in target_equity_keys:
            if k in idx_lower:
                idx = idx_lower.index(k)
                equity_val = bs.iloc[idx, 0]
                break
                
        # Total Assets の検索
        target_assets_keys = ["totalassets", "assets"]
        for k in target_assets_keys:
            if k in idx_lower:
                idx = idx_lower.index(k)
                assets_val = bs.iloc[idx, 0]
                break
                
        if equity_val is not None and assets_val is not None and assets_val != 0:
            # PandasのNaNやNoneチェックを含めて変換
            val_equity = float(equity_val)
            val_assets = float(assets_val)
            if not pd.isna(val_equity) and not pd.isna(val_assets):
                return (val_equity / val_assets) * 100
    except Exception as e:
        print(f"Error calculating equity ratio for {ticker_obj.ticker}: {e}")
    return None

def _fetch_data_sync(ticker: str, company_name_map: Dict[str, str], selected_fields: List[str]) -> Dict[str, Any]:
    """1つのティッカーに対するデータ取得を同期的に行う（スレッド用）。
    必要なフィールドのみをピンポイントで取得する。
    """
    data = {}
    data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["ticker"] = ticker
    data["company_name"] = company_name_map.get(ticker, ticker)
    
    # yfinance.Tickerのインスタンスは、yfinanceの情報を取得する必要がある場合のみ作成
    info_fields = ["price", "per", "pbr", "dividend_yield", "roe", "revenue_growth", "operating_margins"]
    need_info = any(f in selected_fields for f in info_fields) or ("company_name" in selected_fields and ticker not in company_name_map)
    need_equity = "equity_ratio" in selected_fields
    
    if need_info or need_equity:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = {}
            if need_info:
                info = ticker_obj.info or {}
                
            if "company_name" in selected_fields:
                data["company_name"] = info.get("longName") or info.get("shortName") or data["company_name"]
            if "price" in selected_fields:
                data["price"] = info.get("currentPrice") or info.get("regularMarketPrice")
            if "per" in selected_fields:
                data["per"] = info.get("trailingPE") or info.get("forwardPE")
            if "pbr" in selected_fields:
                data["pbr"] = info.get("priceToBook")
            if "dividend_yield" in selected_fields:
                div_y = info.get("dividendYield")
                data["dividend_yield"] = div_y * 100 if div_y is not None else None
            if "roe" in selected_fields:
                roe_val = info.get("returnOnEquity")
                data["roe"] = roe_val * 100 if roe_val is not None else None
            if "revenue_growth" in selected_fields:
                rev_g = info.get("revenueGrowth")
                data["revenue_growth"] = rev_g * 100 if rev_g is not None else None
            if "operating_margins" in selected_fields:
                op_m = info.get("operatingMargins")
                data["operating_margins"] = op_m * 100 if op_m is not None else None
                
            if need_equity:
                data["equity_ratio"] = _get_equity_ratio(ticker_obj)
                
        except Exception as e:
            print(f"Error downloading data for ticker '{ticker}': {e}")
            
    # 選択されたフィールドで、まだ設定されていないものを None で初期化
    for f in selected_fields:
        if f not in data:
            data[f] = None
            
    return data

async def fetch_single_ticker(ticker: str, company_name_map: Dict[str, str], selected_fields: List[str]) -> Dict[str, Any]:
    """非同期でデータ取得を行う"""
    return await asyncio.to_thread(_fetch_data_sync, ticker, company_name_map, selected_fields)

async def fetch_and_save_csv(
    selected_tickers: List[str],
    selected_fields: List[str],
    company_name_map: Dict[str, str],
    output_path: str,
    progress_callback: Callable[[int, int, str], None] = None
) -> str:
    """
    複数銘柄のデータを非同期で取得し、選択されたフィールドのみを抽出してCSVに保存する。
    進捗を progress_callback を通じて通知する。
    """
    results = []
    total = len(selected_tickers)
    
    valid_fields = [f for f in selected_fields if f in FIELD_METADATA]
    if not valid_fields:
        valid_fields = ["date", "ticker", "company_name", "price"]
        
    for idx, ticker in enumerate(selected_tickers, 1):
        if progress_callback:
            progress_callback(idx - 1, total, f"取得中: {ticker}...")
            
        # データ取得
        data = await fetch_single_ticker(ticker, company_name_map, valid_fields)
        results.append(data)
        
        if progress_callback:
            progress_callback(idx, total, f"取得完了: {ticker}")
            
    # DataFrame に変換して整形
    df = pd.DataFrame(results)
    
    # 各行のデータをフォーマット関数で整形
    formatted_rows = []
    for _, row in df.iterrows():
        fmt_row = {}
        for field in valid_fields:
            raw_val = row.get(field, None)
            display_name = FIELD_METADATA[field]["display"]
            
            if pd.isna(raw_val):
                raw_val = None
                
            try:
                fmt_row[display_name] = FIELD_METADATA[field]["fmt"](raw_val)
            except Exception:
                fmt_row[display_name] = "N/A"
                
        formatted_rows.append(fmt_row)
        
    formatted_df = pd.DataFrame(formatted_rows)
    
    # ディレクトリ作成
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # CSVに出力
    formatted_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path

