import os
import sys
import json
import asyncio
import threading
import socket
from datetime import datetime
from contextlib import closing
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import webview
from app.updater import update_master_tickers, hide_file
from app.fetcher import fetch_and_save_csv

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
if getattr(sys, 'frozen', False):
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

# 起動時のマスター銘柄更新
tickers_cache = []

@app.on_event("startup")
async def startup_event():
    global tickers_cache
    tickers_cache = await update_master_tickers()

# ユーザー設定の定義 (書き換え可能データのため data ディレクトリに保存し、隠しファイル化)
CONFIG_PATH = os.path.join(EXE_DIR, "data", "user_config.json")
DEFAULT_CONFIG = {
    "selected_tickers": ["AAPL", "7203.T"],
    "selected_fields": ["date", "ticker", "company_name", "price", "per", "pbr", "dividend_yield", "equity_ratio"],
    "output_path": os.path.join(EXE_DIR, "stock_data.csv"),
    "add_date_to_filename": False
}

def load_user_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 必須のキーが含まれているか確認
                if "selected_tickers" in cfg and "selected_fields" in cfg and "output_path" in cfg:
                    return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_user_config(config: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        # 親フォルダ data も隠しフォルダ化
        hide_file(os.path.dirname(CONFIG_PATH))
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        # 設定ファイル自体も隠しファイル化
        hide_file(CONFIG_PATH)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Pydantic モデル
class ConfigModel(BaseModel):
    selected_tickers: list[str]
    selected_fields: list[str]
    output_path: str
    add_date_to_filename: bool = False

class FetchRequestModel(BaseModel):
    selected_tickers: list[str]
    selected_fields: list[str]
    output_path: str
    add_date_to_filename: bool = False

# API エンドポイント
@app.get("/api/tickers")
async def get_tickers():
    global tickers_cache
    if not tickers_cache:
        master_json_path = os.path.join(EXE_DIR, "data", "master_tickers.json")
        if os.path.exists(master_json_path):
            with open(master_json_path, "r", encoding="utf-8") as f:
                tickers_cache = json.load(f)
        else:
            from app.updater import DEFAULT_TICKERS
            tickers_cache = DEFAULT_TICKERS
    return tickers_cache

@app.get("/api/config")
async def get_config():
    return load_user_config()

@app.post("/api/config/save")
async def save_config_endpoint(config: ConfigModel):
    success = save_user_config(config.dict())
    if not success:
        raise HTTPException(status_code=500, detail="設定の保存に失敗しました。")
    return {"status": "success"}

def run_fetch_task(tickers: list[str], fields: list[str], output_path: str, add_date: bool):
    global progress_state
    progress_state.status = "running"
    progress_state.total = len(tickers)
    progress_state.current = 0
    progress_state.message = "データ取得を開始します..."
    progress_state.output_file = ""
    
    # 銘柄名マップを作成
    company_name_map = {}
    for item in tickers_cache:
        company_name_map[item["ticker"]] = item["name"]
        
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
            
        loop.run_until_complete(
            fetch_and_save_csv(tickers, fields, company_name_map, abs_output_path, progress_cb)
        )
        progress_state.output_file = abs_output_path
        progress_state.status = "completed"
        progress_state.message = f"データの取得が完了しました。保存先: {abs_output_path}"
    except Exception as e:
        progress_state.status = "error"
        progress_state.message = f"データ取得中にエラーが発生しました: {str(e)}"

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
        request.add_date_to_filename
    )
    return {"status": "started"}

@app.get("/api/progress")
async def get_progress():
    return {
        "current": progress_state.current,
        "total": progress_state.total,
        "message": progress_state.message,
        "status": progress_state.status,
        "output_file": progress_state.output_file
    }

@app.get("/api/download")
async def download_file():
    if not progress_state.output_file or not os.path.exists(progress_state.output_file):
        raise HTTPException(status_code=404, detail="出力ファイルが見つかりません。")
    return FileResponse(
        progress_state.output_file, 
        media_type='text/csv', 
        filename=os.path.basename(progress_state.output_file)
    )

# index.html の配信
@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>templates/index.html is not found.</h3>"

# static のマウント
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 空いているポートを探す
def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def run_uvicorn(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    port = find_free_port()
    # FastAPIサーバーをバックグラウンドスレッドで開始
    server_thread = threading.Thread(target=run_uvicorn, args=(port,), daemon=True)
    server_thread.start()
    
    # pywebview 起動
    webview.create_window(
        "Stock Fetcher - 長期投資銘柄情報自動取得ツール",
        f"http://127.0.0.1:{port}",
        width=1100,
        height=800,
        min_size=(900, 650)
    )
    webview.start()
