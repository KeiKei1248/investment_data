"""
出力ファイルパス設定UIコンポーネント
"""

import os
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk


class PathFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="出力先パス:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(10, 5), pady=10)

        self.path_entry = ctk.CTkEntry(self, placeholder_text="出力ファイルの保存先を選択してください...")
        self.path_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        default_output = os.path.abspath("financial_data_raw.csv")
        self.path_entry.insert(0, default_output)

        browse_btn = ctk.CTkButton(self, text="参照...", width=80, command=self._browse_path)
        browse_btn.grid(row=0, column=2, padx=(5, 10), pady=10)

    def _browse_path(self):
        file_path = filedialog.asksaveasfilename(
            title="出力先のCSVファイルを指定",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if file_path:
            self.set_path(file_path)

    def get_path(self) -> str:
        return self.path_entry.get().strip()

    def set_path(self, path_str: str):
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, path_str)
