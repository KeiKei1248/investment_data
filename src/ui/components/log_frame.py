"""
リアルタイムログ表示UIコンポーネント
"""

import queue
import tkinter as tk
import customtkinter as ctk


class LogFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.log_queue = queue.Queue()

        ctk.CTkLabel(self, text="実行ログ", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 2), sticky="w")

        self.log_textbox = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # 100msごとにキューを監視
        self.after(100, self._process_log_queue)

    def log(self, message: str):
        """スレッドセーフなログ追加"""
        self.log_queue.put(message)

    def _process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(tk.END, msg + "\n")
            self.log_textbox.see(tk.END)
            self.log_textbox.configure(state="disabled")
        self.after(100, self._process_log_queue)
