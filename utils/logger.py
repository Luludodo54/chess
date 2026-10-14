"""
utils/logger.py
Configuration simple du logging vers console et fichier.
"""
import logging
import os

def setup_logging(logfile="analysis.log"):
    os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    # file
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
