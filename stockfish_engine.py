"""
stockfish_engine.py
Interface simple vers Stockfish via python-chess.
"""
import chess
import chess.engine
import logging
import shutil
from contextlib import contextmanager

logger = logging.getLogger("chess_assistant")

def find_stockfish_binary(path_hint=None):
    """
    Try to find Stockfish binary. If path_hint provided, check it.
    """
    if path_hint:
        if shutil.which(path_hint):
            return path_hint
        if os.path.exists(path_hint):
            return path_hint
    # try common names in PATH
    for name in ("stockfish", "stockfish.exe"):
        p = shutil.which(name)
        if p:
            return p
    return None

@contextmanager
def open_engine(path):
    engine = None
    try:
        engine = chess.engine.SimpleEngine.popen_uci(path)
        yield engine
    finally:
        if engine:
            try:
                engine.quit()
            except Exception:
                logger.exception("Error closing engine")

def analyze_fen(fen, stockfish_path, time_limit=0.5, depth=None):
    """
    Analyze a FEN position with Stockfish.
    Returns dict with best_move (uci), score (cp or mate), pv (list of uci moves).
    """
    board = chess.Board(fen)
    if not stockfish_path:
        raise FileNotFoundError("Stockfish binary path required")
    res = {}
    with open_engine(stockfish_path) as engine:
        # prefer time limit if given
        limit = chess.engine.Limit(time=time_limit) if time_limit else chess.engine.Limit(depth=depth or 15)
        info = engine.analyse(board, limit, multipv=3)
        # info may be a list of infos if multipv>1
        if isinstance(info, list):
            entries = []
            for i in info:
                score = i.get("score")
                pv = i.get("pv", [])
                entries.append({"score": score, "pv": [m.uci() for m in pv]})
            res["multi"] = entries
            res["best_move"] = entries[0]["pv"][0] if entries and entries[0]["pv"] else None
        else:
            score = info.get("score")
            pv = info.get("pv", [])
            res["score"] = score
            res["pv"] = [m.uci() for m in pv]
            res["best_move"] = res["pv"][0] if res["pv"] else None
    return res
