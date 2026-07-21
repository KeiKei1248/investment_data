"""
データ整形用ユーティリティ関数群 (関数保持部分)
"""

def fmt_percent(val) -> str:
    """数値をパーセント表記 (例: 12.34%) に整形"""
    if val is None:
        return "N/A"
    try:
        return f"{float(val) * 100:.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def fmt_decimal(val, decimals: int = 2) -> str:
    """数値を指定桁数の小数値に整形"""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def fmt_amount(val) -> str:
    """金額等の大数値を 億/兆 単位付き文字列に整形"""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e12:
            return f"{val / 1e12:.2f} 兆"
        elif abs(val) >= 1e8:
            return f"{val / 1e8:.2f} 億"
        else:
            return f"{val:,.0f}"
    except (ValueError, TypeError):
        return "N/A"


FORMATTER_MAP = {
    "percent": fmt_percent,
    "decimal": fmt_decimal,
    "amount": fmt_amount,
}
