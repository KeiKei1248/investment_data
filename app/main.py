import asyncio
import json
import os
import socket
import sys
import threading
from contextlib import closing
from datetime import datetime

import uvicorn
import webview
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.updater import (
    MASTER_FILE,
    get_update_status,
    hide_file,
    load_cached_tickers,
    show_file,
    update_master_tickers_in_background,
)

APP_VERSION = "dev"

app = FastAPI(title="Stock Fetcher")

# CORS設定 (開発時のフロントエンド分離やテストに対応)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 実行ファイルの位置（またはカレントディレクトリ）を特定する
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
    BASE_DIR = sys._MEIPASS
else:
    EXE_DIR = os.getcwd()
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

templates_dir = os.path.join(BASE_DIR, "app", "templates")
static_dir = os.path.join(BASE_DIR, "app", "static")


# 進行状況の保持
class FetchStatus:
    def __init__(self):
        self.current = 0
        self.total = 0
        self.message = "待機中..."
        self.status = "idle"  # idle, running, completed, error
        self.output_file = ""


progress_state = FetchStatus()


@app.on_event("startup")
async def startup_event():
    # 起動時はディレクトリの準備のみ行う（起動超高速化）
    os.makedirs("data", exist_ok=True)
    hide_file("data")


# ユーザー設定の定義 (書き換え可能データのため data ディレクトリに保存し、隠しファイル化)
CONFIG_PATH = os.path.join(EXE_DIR, "data", "user_config.json")
DEFAULT_CONFIG = {
    "selected_category": "プライム（内国株式）",
    "selected_tickers": ["7203.T"],
    "selected_fields": [
        "date",
        "ticker",
        "company_name",
        "price",
        "per",
        "pbr",
        "dividend_yield",
        "equity_ratio",
    ],
    "output_path": os.path.join(EXE_DIR, "stock_data.csv"),
    "add_date_to_filename": False,
    "master_last_updated": "",
}


def load_user_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 必須のキーが含まれているか確認
                if (
                    "selected_tickers" in cfg
                    and "selected_fields" in cfg
                    and "output_path" in cfg
                ):
                    # 移行対応 (selected_categoryが無い、または古いselected_segmentがある場合)
                    if "selected_category" not in cfg:
                        if "selected_segment" in cfg:
                            cfg["selected_category"] = cfg.pop("selected_segment")
                        else:
                            cfg["selected_category"] = "プライム（内国株式）"
                    if "master_last_updated" not in cfg:
                        cfg["master_last_updated"] = ""

                    # 移行対応: 出力先が「株式情報」フォルダを含む古いデフォルトの場合、EXE_DIR直下に戻す
                    old_folder_path = os.path.join(
                        EXE_DIR, "株式情報", "stock_data.csv"
                    )
                    if (
                        os.path.abspath(cfg["output_path"])
                        == os.path.abspath(old_folder_path)
                        or cfg["output_path"] == "株式情報/stock_data.csv"
                    ):
                        cfg["output_path"] = os.path.join(EXE_DIR, "stock_data.csv")

                    return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG


def save_user_config(config: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        hide_file(os.path.dirname(CONFIG_PATH))
        show_file(CONFIG_PATH)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        hide_file(CONFIG_PATH)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


# Pydantic モデル
class ConfigModel(BaseModel):
    selected_category: str = ""
    selected_tickers: list[str]
    selected_fields: list[str]
    output_path: str
    add_date_to_filename: bool = False
    master_last_updated: str = ""


class FetchRequestModel(BaseModel):
    selected_category: str = ""
    selected_tickers: list[str]
    selected_fields: list[str]
    output_path: str
    add_date_to_filename: bool = False


# API エンドポイント
@app.get("/api/tickers")
async def get_tickers(background_tasks: BackgroundTasks = None):
    # 1. ローカルキャッシュ（高速）を即座に読み込み
    tickers = load_cached_tickers()

    # 30日以上経過しているかどうかのチェック
    config = load_user_config()
    last_updated_str = config.get("master_last_updated", "")

    should_update = False
    if not last_updated_str:
        should_update = True
    else:
        try:
            last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d")
            delta = datetime.now() - last_updated
            if delta.days >= 30:
                should_update = True
        except ValueError:
            should_update = True

    # キャッシュファイル自体が存在しない場合も更新
    if not os.path.exists(MASTER_FILE):
        should_update = True

    # 同期完了コールバック
    def on_sync_complete():
        cfg = load_user_config()
        cfg["master_last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_user_config(cfg)

    # 2. 条件を満たす場合のみ、バックグラウンドタスクで最新のデータをスクレイピング・更新開始
    if should_update and background_tasks:
        background_tasks.add_task(update_master_tickers_in_background, on_sync_complete)

    return tickers


@app.post("/api/tickers/update")
async def force_update_tickers(background_tasks: BackgroundTasks):
    # 手動更新なので強制的にバックグラウンド同期を実行
    def on_sync_complete():
        cfg = load_user_config()
        cfg["master_last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_user_config(cfg)

    background_tasks.add_task(update_master_tickers_in_background, on_sync_complete)
    return {"status": "started"}


@app.get("/api/tickers/status")
async def get_tickers_status():
    # 同期ステータスを返す
    return {"status": get_update_status()}


@app.get("/api/config")
async def get_config():
    return load_user_config()


@app.post("/api/config/save")
async def save_config_endpoint(config: ConfigModel):
    success = save_user_config(config.dict())
    if not success:
        raise HTTPException(status_code=500, detail="設定の保存に失敗しました。")
    return {"status": "success"}


def run_fetch_task(
    tickers: list[str], fields: list[str], output_path: str, add_date: bool
):
    global progress_state
    progress_state.status = "running"
    progress_state.total = len(tickers)
    progress_state.current = 0
    progress_state.message = "データ取得を開始します..."
    progress_state.output_file = ""

    # 日本株のキャッシュから銘柄名マップを作成
    cached_tickers = load_cached_tickers()
    tickers_list = cached_tickers.get("japan", [])
    company_name_map = {item["ticker"]: item["name"] for item in tickers_list}

    def progress_cb(current: int, total: int, msg: str):
        progress_state.current = current
        progress_state.total = total
        progress_state.message = msg

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        abs_output_path = os.path.abspath(output_path)

        # ファイル名に日付を付与するオプションの適用
        if add_date:
            dir_name = os.path.dirname(abs_output_path)
            base_name = os.path.basename(abs_output_path)
            name, ext = os.path.splitext(base_name)
            date_str = datetime.now().strftime("%Y%m%d")
            abs_output_path = os.path.join(dir_name, f"{name}_{date_str}{ext}")

        from app.fetcher import fetch_and_save_csv

        loop.run_until_complete(
            fetch_and_save_csv(
                tickers, fields, company_name_map, abs_output_path, progress_cb
            )
        )
        progress_state.output_file = abs_output_path
        progress_state.status = "completed"
        progress_state.message = (
            f"データの取得が完了しました。保存先: {abs_output_path}"
        )
    except Exception as e:
        progress_state.status = "error"
        progress_state.message = f"データ取得中にエラーが発生しました: {e!s}"


@app.post("/api/fetch")
async def start_fetch(request: FetchRequestModel, background_tasks: BackgroundTasks):
    global progress_state
    if progress_state.status == "running":
        raise HTTPException(status_code=400, detail="既にデータ取得処理が実行中です。")

    # 最新のパラメータ設定を保存
    save_user_config(request.dict())

    background_tasks.add_task(
        run_fetch_task,
        request.selected_tickers,
        request.selected_fields,
        request.output_path,
        request.add_date_to_filename,
    )
    return {"status": "started"}


@app.get("/api/progress")
async def get_progress():
    return {
        "current": progress_state.current,
        "total": progress_state.total,
        "message": progress_state.message,
        "status": progress_state.status,
        "output_file": progress_state.output_file,
    }


# index.html の配信
@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content.replace("__VERSION__", APP_VERSION)
    return "<h3>templates/index.html is not found.</h3>"


# static のマウント
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# 空いているポートを探す
def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def run_uvicorn(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


window = None

if __name__ == "__main__":
    port = find_free_port()
    # FastAPIサーバーをバックグラウンドスレッドで開始
    server_thread = threading.Thread(target=run_uvicorn, args=(port,), daemon=True)
    server_thread.start()

    # pywebview 起動
    window = webview.create_window(
        "Stock Fetcher - 長期投資銘柄情報自動取得ツール (日本株専用)",
        f"http://127.0.0.1:{port}",
        width=1150,
        height=850,
        min_size=(950, 700),
    )
    webview.start()
