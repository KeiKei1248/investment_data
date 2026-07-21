"""
企業選択・指標選択UIコンポーネント
"""

import customtkinter as ctk
from typing import Dict, List, Tuple
from src.constants import MASTER_TICKERS, MASTER_METRICS


class SelectionFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.ticker_vars: Dict[str, ctk.BooleanVar] = {}
        self.metric_vars: Dict[str, ctk.BooleanVar] = {}

        self._build_ticker_panel()
        self._build_metric_panel()

    def _build_ticker_panel(self):
        ticker_panel = ctk.CTkFrame(self, fg_color="transparent")
        ticker_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        t_header = ctk.CTkFrame(ticker_panel, fg_color="transparent")
        t_header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(t_header, text="対象企業選択", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(t_header, text="全解除", width=60, height=24, command=self.deselect_all_tickers).pack(side="right", padx=(5, 0))
        ctk.CTkButton(t_header, text="全選択", width=60, height=24, command=self.select_all_tickers).pack(side="right")

        t_scroll = ctk.CTkScrollableFrame(ticker_panel, height=200)
        t_scroll.pack(fill="both", expand=True)

        for sym, name in MASTER_TICKERS:
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(t_scroll, text=f"{sym} ({name})", variable=var)
            chk.pack(anchor="w", pady=3, padx=5)
            self.ticker_vars[sym] = var

    def _build_metric_panel(self):
        metric_panel = ctk.CTkFrame(self, fg_color="transparent")
        metric_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        m_header = ctk.CTkFrame(metric_panel, fg_color="transparent")
        m_header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(m_header, text="出力指標選択", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(m_header, text="全解除", width=60, height=24, command=self.deselect_all_metrics).pack(side="right", padx=(5, 0))
        ctk.CTkButton(m_header, text="全選択", width=60, height=24, command=self.select_all_metrics).pack(side="right")

        m_scroll = ctk.CTkScrollableFrame(metric_panel, height=200)
        m_scroll.pack(fill="both", expand=True)

        for key, name, _ in MASTER_METRICS:
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(m_scroll, text=name, variable=var)
            chk.pack(anchor="w", pady=3, padx=5)
            self.metric_vars[key] = var

    # 選択/解除操作
    def select_all_tickers(self):
        for var in self.ticker_vars.values():
            var.set(True)

    def deselect_all_tickers(self):
        for var in self.ticker_vars.values():
            var.set(False)

    def select_all_metrics(self):
        for var in self.metric_vars.values():
            var.set(True)

    def deselect_all_metrics(self):
        for var in self.metric_vars.values():
            var.set(False)

    # 選択状態の取得 / 設定
    def get_selected_tickers(self) -> List[str]:
        return [sym for sym, var in self.ticker_vars.items() if var.get()]

    def get_selected_metrics(self) -> List[str]:
        return [key for key, var in self.metric_vars.items() if var.get()]

    def set_selected_tickers(self, selected_symbols: List[str]):
        for sym, var in self.ticker_vars.items():
            var.set(sym in selected_symbols)

    def set_selected_metrics(self, selected_keys: List[str]):
        for key, var in self.metric_vars.items():
            var.set(key in selected_keys)
