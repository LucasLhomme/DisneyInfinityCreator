"""First launch: extract the base figures from the player's own game install before Creator opens."""
import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from src.core import game_data
from src.core.config import load_settings, save_settings

ACCENT, RED, GREEN = "#fbbf24", "#f87171", "#4ade80"


class SetupWindow(ctk.CTk):
    """Returns with `self.done` True once the game data is extracted (False if the window was closed)."""

    def __init__(self):
        super().__init__()
        self.title("Disney Infinity Creator - first launch")
        self.geometry("620x380")
        self.resizable(False, False)
        self.done, self._worker, self._events = False, None, queue.Queue()
        self.settings = load_settings()
        pad = {"padx": 20, "sticky": "ew"}
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="First launch: extract the game data", font=ctk.CTkFont(size=18, weight="bold")
                     ).grid(row=0, column=0, pady=(18, 4), **pad)
        ctk.CTkLabel(self, justify="left", wraplength=580, text=(
            "Creator builds its base figures (models, animations, preview textures) from your own copy of "
            "Disney Infinity 3.0. Nothing from the game is shipped with Creator. This is done once and takes a "
            "few minutes.")).grid(row=1, column=0, pady=(0, 12), **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, **pad)
        row.grid_columnconfigure(0, weight=1)
        self.path = ctk.CTkEntry(row, placeholder_text="Disney Infinity 3.0 Gold Edition folder")
        self.path.grid(row=0, column=0, sticky="ew")
        found = game_data.find_game_dir(self.settings.get("game_path", ""))
        if found:
            self.path.insert(0, found)
        ctk.CTkButton(row, text="Browse...", width=90, command=self._browse).grid(row=0, column=1, padx=(8, 0))
        self.status = ctk.CTkLabel(self, text="" if found else "Select the game folder (it holds assets\\characters).",
                                   text_color=GREEN if found else ACCENT, anchor="w")
        self.status.grid(row=3, column=0, pady=(6, 6), **pad)
        self.bar = ctk.CTkProgressBar(self)
        self.bar.set(0)
        self.bar.grid(row=4, column=0, pady=(4, 4), **pad)
        self.detail = ctk.CTkLabel(self, text="", anchor="w", text_color="gray70")
        self.detail.grid(row=5, column=0, **pad)
        self.button = ctk.CTkButton(self, text="Extract and start Creator", fg_color=ACCENT, text_color="#09090b",
                                    hover_color="#f59e0b", font=ctk.CTkFont(weight="bold"), command=self._start)
        self.button.grid(row=6, column=0, pady=(16, 18), **pad)
        if found:
            self.status.configure(text=f"Game found: {found}")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _browse(self):
        folder = filedialog.askdirectory(title="Disney Infinity 3.0 Gold Edition folder")
        if folder:
            self.path.delete(0, "end")
            self.path.insert(0, folder)
            ok = game_data.is_game_dir(folder)
            self.status.configure(text="Game found." if ok else "This is not the game folder (no assets\\characters).",
                                  text_color=GREEN if ok else RED)

    def _start(self):
        folder = self.path.get().strip().strip('"')
        if not game_data.is_game_dir(folder):
            self.status.configure(text="This is not the game folder (no assets\\characters).", text_color=RED)
            return
        self.settings["game_path"] = folder
        save_settings(self.settings)
        self.button.configure(state="disabled", text="Extracting...")
        self.path.configure(state="disabled")
        self.status.configure(text="Extracting the base figures...", text_color=ACCENT)

        def work():
            try:
                count = game_data.extract(folder, log=lambda s: None,
                                          progress=lambda i, n, name: self._events.put(("progress", i, n, name)))
                self._events.put(("done", count))
            except Exception as exc:  # noqa: BLE001 - shown in the window
                self._events.put(("error", str(exc)))
        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()
        self.after(100, self._poll)

    def _poll(self):
        try:
            while True:
                event = self._events.get_nowait()
                if event[0] == "progress":
                    _, i, n, name = event
                    self.bar.set(i / max(n, 1))
                    self.detail.configure(text=f"{i}/{n}  {name}")
                elif event[0] == "done":
                    self.done = True
                    self.status.configure(text=f"{event[1]} figures extracted.", text_color=GREEN)
                    self.after(600, self.destroy)
                    return
                else:
                    self.status.configure(text=f"Extraction failed: {event[1]}", text_color=RED)
                    self.button.configure(state="normal", text="Try again")
                    self.path.configure(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _close(self):
        if self._worker is not None and self._worker.is_alive():
            return  # an interrupted extraction would leave a half-built pack
        self.destroy()
