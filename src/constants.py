"""
アプリケーション全体の定数およびマスタデータ定義
"""

CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "KeiKei1248/investment_data"
CONFIG_FILE = "config.json"

# マスタ定義: 企業リスト [(シンボル, 企業名)]
MASTER_TICKERS = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corp."),
    ("GOOGL", "Alphabet Inc."),
    ("AMZN", "Amazon.com Inc."),
    ("NVDA", "NVIDIA Corp."),
    ("7203.T", "トヨタ自動車"),
    ("9984.T", "ソフトバンクグループ"),
    ("6758.T", "ソニーグループ"),
    ("6861.T", "キーエンス"),
    ("7974.T", "任天堂"),
    ("6501.T", "日立製作所"),
    ("8058.T", "三菱商事")
]

# マスタ定義: 指標リスト [(キー, 表示名, フォーマット関数名)]
MASTER_METRICS = [
    ("currentPrice", "現在株価", "decimal"),
    ("trailingPE", "PER (予想/実績)", "decimal"),
    ("priceToBook", "PBR", "decimal"),
    ("returnOnEquity", "ROE", "percent"),
    ("returnOnAssets", "ROA", "percent"),
    ("dividendYield", "配当利回り", "percent"),
    ("operatingMargins", "営業利益率", "percent"),
    ("freeCashflow", "フリーキャッシュフロー", "amount"),
]
