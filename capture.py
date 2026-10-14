"""
capture.py
Fonctions pour capturer l'écran (zone complète ou région).
Utilise mss pour compatibilité Windows.
"""
import numpy as np
import mss
import cv2
from PIL import Image

def grab_screen(region=None):
    """
    Capture the whole screen or a region.
    region = dict(left=, top=, width=, height=) or None
    Returns BGR image (OpenCV format)
    """
    with mss.mss() as sct:
        if region:
            monitor = {"left": region["left"], "top": region["top"],
                       "width": region["width"], "height": region["height"]}
        else:
            monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img_bgr
