"""
ヘッダーUIコンポーネント (タイトル + アップデートボタン)
"""

import customtkinter as ctk
from typing import Callable


class HeaderFrame(ctk.CTkFrame):
    def __init__(self, master, on_update_click: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.on_update_click = on_update_click

        self.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            self,
            text="財務RAWデータ抽出ツール (Yahoo Finance)",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        # 新バージョン通知ボタン（初期非表示）
        self.update_btn = ctk.CTkButton(
            self,
            text="⚠️ 新バージョンあり",
            fg_color="#D32F2F",
            hover_color="#9A0007",
            command=self.on_update_click
        )

    def show_update_button(self, latest_tag: str):
        self.update_btn.configure(text=f"⚠️ 新バージョンあり (v{latest_tag})")
        self.update_btn.grid(row=0, column=1, sticky="e")
