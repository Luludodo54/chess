"""
gui.py
Interface graphique minimaliste en CustomTkinter (si dispo) sinon Tkinter.
- Bouton Start/Stop
- Affiche capture (dernier plateau warpé)
- Affiche meilleur coup et liste des variantes obtenues
- Zone log (text)
- Permet d'entrer un FEN manuellement pour correction
"""
import threading
import time
import io
import os
import logging
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except Exception:
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    CTK_AVAILABLE = False

from PIL import Image, ImageTk
import chess
import numpy as np
import cv2

from capture import grab_screen
from board_recognition import image_to_board
from stockfish_engine import analyze_fen, find_stockfish_binary
from utils.logger import setup_logging

logger = logging.getLogger("chess_assistant")
setup_logging("analysis.log")

RUN_INTERVAL = 1.5  # seconds between captures when running

class AnalyzerThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        last_fen = None
        while not self._stop.is_set():
            try:
                img = grab_screen()
                board, warped, ok, msg = image_to_board(img, templates_dir=self.app.templates_dir)
                self.app.log(f"Detection: {msg}")
                if not ok or board is None:
                    # show warped if exists, then wait
                    if warped is not None:
                        self.app.update_board_image(warped)
                    else:
                        self.app.log("No valid board found in capture.")
                    time.sleep(RUN_INTERVAL)
                    continue
                fen = board.fen()
                self.app.update_board_image(warped)
                if fen != last_fen:
                    last_fen = fen
                    self.app.log(f"New position FEN: {fen}")
                    # run analysis
                    stockfish_path = self.app.stockfish_path or find_stockfish_binary()
                    if not stockfish_path:
                        self.app.log("Stockfish binary not configured/found.")
                    else:
                        res = analyze_fen(fen, stockfish_path, time_limit=0.5)
                        # normalize result for display
                        self.app.show_analysis(fen, res)
                time.sleep(RUN_INTERVAL)
            except Exception as e:
                logger.exception("Error in analyzer thread")
                self.app.log(f"Error: {e}")
                time.sleep(RUN_INTERVAL)

class App:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.analyzer = None
        self.templates_dir = "templates"
        self.stockfish_path = None
        self.img_tk = None
        self.setup_ui()

    def setup_ui(self):
        if CTK_AVAILABLE:
            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")
            self.root.geometry("1000x700")
            self.root.title("Assistant d'échecs - Minimal")
            frame = ctk.CTkFrame(self.root)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            # Left: image
            self.canvas = ctk.CTkLabel(frame, text="")
            self.canvas.grid(row=0, column=0, rowspan=6, padx=10, pady=10)
            # Controls
            self.btn_start = ctk.CTkButton(frame, text="Start", command=self.toggle)
            self.btn_start.grid(row=0, column=1, sticky="ew")
            self.entry_stockfish = ctk.CTkEntry(frame, placeholder_text="Stockfish path (optional)")
            self.entry_stockfish.grid(row=1, column=1, sticky="ew")
            self.btn_set_stockfish = ctk.CTkButton(frame, text="Set Stockfish", command=self.set_stockfish)
            self.btn_set_stockfish.grid(row=2, column=1, sticky="ew")
            self.lbl_best = ctk.CTkLabel(frame, text="Meilleur coup: -")
            self.lbl_best.grid(row=3, column=1, sticky="w")
            self.list_moves = ctk.CTkTextbox(frame, width=300, height=200)
            self.list_moves.grid(row=4, column=1, sticky="nsew")
            self.text_log = ctk.CTkTextbox(frame, width=300, height=150)
            self.text_log.grid(row=5, column=1, sticky="nsew")
        else:
            self.root.geometry("1000x700")
            self.root.title("Assistant d'échecs - Minimal")
            frame = tk.Frame(self.root)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            self.canvas = tk.Label(frame)
            self.canvas.grid(row=0, column=0, rowspan=6, padx=10, pady=10)
            self.btn_start = tk.Button(frame, text="Start", command=self.toggle)
            self.btn_start.grid(row=0, column=1, sticky="ew")
            self.entry_stockfish = tk.Entry(frame)
            self.entry_stockfish.grid(row=1, column=1, sticky="ew")
            self.btn_set_stockfish = tk.Button(frame, text="Set Stockfish", command=self.set_stockfish)
            self.btn_set_stockfish.grid(row=2, column=1, sticky="ew")
            self.lbl_best = tk.Label(frame, text="Meilleur coup: -")
            self.lbl_best.grid(row=3, column=1, sticky="w")
            self.list_moves = tk.Text(frame, width=40, height=12)
            self.list_moves.grid(row=4, column=1, sticky="nsew")
            self.text_log = tk.Text(frame, width=40, height=8)
            self.text_log.grid(row=5, column=1, sticky="nsew")
        # Menu for manual FEN entry
        menu = getattr(self.root, "menu", None)
        # simple keyboard
        self.root.bind("<Control-e>", lambda e: self.prompt_fen())

    def toggle(self):
        if not self.running:
            self.start()
        else:
            self.stop()

    def start(self):
        self.btn_start.config(text="Stop")
        self.running = True
        self.analyzer = AnalyzerThread(self)
        self.analyzer.start()
        self.log("Analysis started.")

    def stop(self):
        self.btn_start.config(text="Start")
        self.running = False
        if self.analyzer:
            self.analyzer.stop()
            self.analyzer = None
        self.log("Analysis stopped.")

    def set_stockfish(self):
        val = self.entry_stockfish.get().strip()
        if val:
            self.stockfish_path = val
            self.log(f"Stockfish set to: {val}")

    def update_board_image(self, warped_img):
        # convert BGR->PIL Image
        img_rgb = cv2.cvtColor(warped_img, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img_rgb)
        pil = pil.resize((480,480))
        self.img_tk = ImageTk.PhotoImage(pil)
        if CTK_AVAILABLE:
            self.canvas.configure(image=self.img_tk)
            self.canvas.image = self.img_tk
        else:
            self.canvas.config(image=self.img_tk)
            self.canvas.image = self.img_tk

    def show_analysis(self, fen, res):
        # display best move and variants
        best_move = res.get("best_move")
        multi = res.get("multi")
        self.lbl_best.config(text=f"Meilleur coup: {best_move}")
        self.list_moves.delete("1.0", "end")
        if multi:
            for i, entry in enumerate(multi, start=1):
                score = entry["score"]
                pv = " ".join(entry["pv"])
                self.list_moves.insert("end", f"{i}. {pv}  score={score}\n")
        else:
            pv = res.get("pv", [])
            self.list_moves.insert("end", f"pv: {' '.join(pv)}\nscore: {res.get('score')}\n")
        self.log(f"Analysis result: best={best_move}")

    def log(self, text):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.text_log.insert("end", f"[{ts}] {text}\n")
        self.text_log.see("end")

    def prompt_fen(self):
        # simple prompt to enter FEN and analyze it
        def submit():
            fen = entry.get().strip()
            top.destroy()
            try:
                board = chess.Board(fen)
                self.log(f"Manual FEN set: {fen}")
                stockfish_path = self.stockfish_path or find_stockfish_binary()
                if not stockfish_path:
                    self.log("Stockfish path not set.")
                    return
                res = analyze_fen(fen, stockfish_path, time_limit=0.5)
                self.show_analysis(fen, res)
            except Exception as e:
                self.log(f"Invalid FEN: {e}")

        top = tk.Toplevel(self.root)
        top.title("Entrer FEN manuellement")
        tk.Label(top, text="FEN:").pack(side="left")
        entry = tk.Entry(top, width=80)
        entry.pack(side="left")
        btn = tk.Button(top, text="OK", command=submit)
        btn.pack(side="left")

def run_gui():
    if CTK_AVAILABLE:
        app_root = ctk.CTk()
    else:
        app_root = __import__("tkinter").Tk()
    app = App(app_root)
    app_root.mainloop()
