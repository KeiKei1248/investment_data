"""
メインウィンドウ (UI全体の統括とイベント制御)
"""

import threading
import webbrowser
from tkinter import messagebox
import customtkinter as ctk

from src.constants import CURRENT_VERSION, GITHUB_REPO, CONFIG_FILE
from src.backend.config_manager import load_config, save_config
from src.backend.updater import check_for_updates
from src.backend.fetcher import fetch_and_export_csv
from src.ui.components.header_frame import HeaderFrame
from src.ui.components.selection_frame import SelectionFrame
from src.ui.components.path_frame import PathFrame
from src.ui.components.log_frame import LogFrame


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ウィンドウ基本設定
        self.title(f"株式財務RAWデータ抽出ツール v{CURRENT_VERSION}")
        self.geometry("900x750")
        self.minsize(800, 650)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.latest_release_url = ""

        # UIコンポーネントの配置
        self._build_layout()

        # 設定の復元
        self._restore_config()

        # アップデート確認スレッドの開始
        threading.Thread(target=self._run_update_check, daemon=True).start()

    def _build_layout(self):
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. ヘッダー
        self.header_frame = HeaderFrame(self, on_update_click=self._on_update_click)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        # 2. 選択パネル (企業 & 指標)
        self.selection_frame = SelectionFrame(self)
        self.selection_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # 3. 出力先設定パネル
        self.path_frame = PathFrame(self)
        self.path_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        # 4. 実行ボタン
        self.run_btn = ctk.CTkButton(
            self,
            text="🚀 CSVデータを出力・保存",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#1F6AA5",
            hover_color="#144870",
            command=self._start_export
        )
        self.run_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # 5. ログ表示パネル
        self.log_frame = LogFrame(self)
        self.log_frame.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="nsew")

    # ==========================================
    # 設定の復元と保存
    # ==========================================
    def _restore_config(self):
        cfg = load_config(CONFIG_FILE)
        if not cfg:
            return

        out_path = cfg.get("output_path")
        if out_path:
            self.path_frame.set_path(out_path)

        sel_tickers = cfg.get("selected_tickers")
        if isinstance(sel_tickers, list):
            self.selection_frame.set_selected_tickers(sel_tickers)

        sel_metrics = cfg.get("selected_metrics")
        if isinstance(sel_metrics, list):
            self.selection_frame.set_selected_metrics(sel_metrics)

        self.log_frame.log("設定ファイル (config.json) を読み込みました。")

    def _persist_config(self):
        cfg = {
            "output_path": self.path_frame.get_path(),
            "selected_tickers": self.selection_frame.get_selected_tickers(),
            "selected_metrics": self.selection_frame.get_selected_metrics()
        }
        if save_config(CONFIG_FILE, cfg):
            self.log_frame.log("設定を config.json に保存しました。")
        else:
            self.log_frame.log("設定の保存に失敗しました。")

    # ==========================================
    # アップデート通知処理
    # ==========================================
    def _run_update_check(self):
        has_update, latest_tag, release_url = check_for_updates(GITHUB_REPO, CURRENT_VERSION)
        if has_update and latest_tag:
            self.latest_release_url = release_url or ""
            self.after(0, lambda: self.header_frame.show_update_button(latest_tag))

    def _on_update_click(self):
        url = self.latest_release_url or f"https://github.com/{GITHUB_REPO}/releases"
        webbrowser.open(url)

    # ==========================================
    # CSV出力・データ取得の非同期実行
    # ==========================================
    def _start_export(self):
        selected_symbols = self.selection_frame.get_selected_tickers()
        selected_metric_keys = self.selection_frame.get_selected_metrics()
        output_path = self.path_frame.get_path()

        if not selected_symbols:
            messagebox.showwarning("警告", "企業が1つも選択されていません。")
            return
        if not selected_metric_keys:
            messagebox.showwarning("警告", "指標が1つも選択されていません。")
            return
        if not output_path:
            messagebox.showwarning("警告", "出力先パスを指定してください。")
            return

        # UIの変更 & 設定保存
        self.run_btn.configure(state="disabled", text="データ取得中...")
        self._persist_config()

        # 処理スレッド開始
        threading.Thread(
            target=self._worker_export,
            args=(selected_symbols, selected_metric_keys, output_path),
            daemon=True
        ).start()

    def _worker_export(self, symbols, metrics, path):
        try:
            success = fetch_and_export_csv(
                selected_symbols=symbols,
                selected_metric_keys=metrics,
                output_path=path,
                log_callback=self.log_frame.log
            )
            if success:
                self.after(0, lambda: messagebox.showinfo("完了", f"データの抽出とCSV保存が完了しました。\n保存先: {path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("エラー", f"エラーが発生しました:\n{e}"))
        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal", text="🚀 CSVデータを出力・保存"))
