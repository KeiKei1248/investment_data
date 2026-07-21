"""
yfinance データ取得および CSV 出力処理ロジック (バックエンド部分)
"""

import os
import pandas as pd
import yfinance as yf
from typing import Callable, List, Dict
from src.constants import MASTER_TICKERS, MASTER_METRICS
from src.utils.formatters import FORMATTER_MAP


def fetch_and_export_csv(
    selected_symbols: List[str],
    selected_metric_keys: List[str],
    output_path: str,
    log_callback: Callable[[str], None]
) -> bool:
    """
    Yahoo Finance から財務データを取得し、選択された順序を厳密保持して CSV に出力する。
    """
    log_callback("==========================================")
    log_callback("データ取得処理を開始します...")

    # 指標メタ情報・名前マップ準備
    metric_meta = {}
    for key, display_name, fmt_type in MASTER_METRICS:
        fmt_fn = FORMATTER_MAP.get(fmt_type, lambda x: str(x) if x is not None else "N/A")
        metric_meta[key] = (display_name, fmt_fn)

    ticker_name_map: Dict[str, str] = dict(MASTER_TICKERS)

    rows = []
    total = len(selected_symbols)

    # MASTER_TICKERS で定義された順序を厳密に保持してループ実行
    for idx, sym in enumerate(selected_symbols, 1):
        comp_name = ticker_name_map.get(sym, sym)
        log_callback(f"[{idx}/{total}] {sym} ({comp_name}) のデータ取得中...")

        row_dict = {
            "Ticker": sym,
            "企業名": comp_name
        }

        try:
            ticker_obj = yf.Ticker(sym)
            info = ticker_obj.info or {}

            for key in selected_metric_keys:
                display_name, fmt_fn = metric_meta[key]
                raw_val = info.get(key)

                # 株価のフォールバック取得
                if key == "currentPrice" and raw_val is None:
                    raw_val = info.get("regularMarketPrice")

                row_dict[display_name] = fmt_fn(raw_val)

            log_callback(f" -> {sym}: 取得成功")
        except Exception as e:
            log_callback(f" -> {sym}: 取得エラー ({e})")
            for key in selected_metric_keys:
                display_name, _ = metric_meta[key]
                if display_name not in row_dict:
                    row_dict[display_name] = "エラー"

        rows.append(row_dict)

    # DataFrame 作成および CSV 出力
    try:
        df = pd.DataFrame(rows)

        # 保存先ディレクトリの作成確認
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Excel 文字化け対策のため utf-8-sig で保存
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        log_callback(f"✅ 保存完了: {output_path}")
        log_callback("==========================================")
        return True
    except Exception as e:
        log_callback(f"❌ CSV書き込み失敗: {e}")
        raise e
