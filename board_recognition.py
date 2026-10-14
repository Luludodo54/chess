"""
board_recognition.py
Détection du plateau (repérage du carré), transformation perspective, découpage en 8x8 cellules
et reconnaissance de pièces par template matching si des templates sont fournis.

Limitations :
- Ce module réalise une méthode heuristique robuste pour des vues proches du plan.
- Pour des captures complexes/angles forts, il faudra entraîner un modèle ML.
"""
import cv2
import numpy as np
import os
import chess

# Mapping template filename keys to piece letters in FEN (white uppercase)
TEMPLATE_NAME_MAP = {
    "wP": "P", "wN": "N", "wB": "B", "wR": "R", "wQ": "Q", "wK": "K",
    "bP": "p", "bN": "n", "bB": "b", "bR": "r", "bQ": "q", "bK": "k",
}

def find_board_contour(img):
    """
    Find the largest roughly-square contour which should correspond to the board.
    Returns contour or None.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # edges
    edges = cv2.Canny(thresh, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_area = 0
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10000:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > max_area:
            max_area = area
            best = approx
    return best

def order_corners(pts):
    # pts: 4x1x2
    pts = pts.reshape(4,2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype="float32")

def warp_board(img, board_contour, size=800):
    """
    Perspective transform to get top-down view of board.
    """
    rect = order_corners(board_contour)
    dst = np.array([[0,0],[size-1,0],[size-1,size-1],[0,size-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (size, size))
    return warped, M

def split_cells(board_img):
    """
    Split the top-down board image into 8x8 cell images.
    Returns list of lists (rank 8 to 1, file a to h).
    """
    h, w = board_img.shape[:2]
    cell_h = h // 8
    cell_w = w // 8
    cells = []
    for r in range(8):
        row = []
        for c in range(8):
            y1 = r * cell_h
            x1 = c * cell_w
            cell = board_img[y1:y1+cell_h, x1:x1+cell_w].copy()
            row.append(cell)
        cells.append(row)
    return cells

def load_templates(dirpath):
    """
    Load templates from a directory.
    Expected filenames like wP.png, bK.png, etc. (see TEMPLATE_NAME_MAP)
    Returns dict key->gray image
    """
    templates = {}
    if not os.path.isdir(dirpath):
        return templates
    for fname in os.listdir(dirpath):
        name, ext = os.path.splitext(fname)
        if name in TEMPLATE_NAME_MAP:
            path = os.path.join(dirpath, fname)
            tpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if tpl is not None:
                templates[name] = tpl
    return templates

def recognize_with_templates(cells, templates, match_threshold=0.55):
    """
    For each cell, run template matching against all templates.
    Returns a board object (python-chess.Board) and a boolean flag if detection seems OK.
    """
    board = chess.Board.empty()  # start empty
    ok = True
    if not templates:
        return None, False
    for r in range(8):
        for c in range(8):
            cell = cells[r][c]
            gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
            best_val = 0
            best_key = None
            for key, tpl in templates.items():
                # resize template if needed
                tpl_resized = cv2.resize(tpl, (gray.shape[1], gray.shape[0]))
                res = cv2.matchTemplate(gray, tpl_resized, cv2.TM_CCOEFF_NORMED)
                _, maxval, _, _ = cv2.minMaxLoc(res)
                if maxval > best_val:
                    best_val = maxval
                    best_key = key
            if best_val >= match_threshold and best_key:
                fen_char = TEMPLATE_NAME_MAP[best_key]
                # chess.Board expects rank 8->1, file a->h. Our r=0 is top row (rank 8).
                square_index = chess.square(c, 7 - r)
                board.set_piece_at(square_index, chess.Piece.from_symbol(fen_char))
            # else leave empty (or set ok=False to indicate uncertain)
            else:
                # mark uncertainty if many empty cells are ambiguous
                # we don't fail immediately; caller can decide
                pass
    return board, ok

def heuristic_detect_pieces(cells, empty_threshold=0.12):
    """
    Very simple heuristic: compare cell mean intensity to local median.
    Returns a Board and confidence flag.
    """
    board = chess.Board.empty()
    confidences = []
    for r in range(8):
        for c in range(8):
            cell = cells[r][c]
            gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
            # normalize and compute variance/mean
            mean = float(np.mean(gray)) / 255.0
            std = float(np.std(gray)) / 255.0
            # Heuristic: if std is large enough, assume there is a piece
            if std > 0.07 or mean < 0.45 or mean > 0.55:
                # We can't tell which piece; place a pawn as placeholder to allow analysis
                square_index = chess.square(c, 7 - r)
                # Default to white pawn if mean is lighter, else black pawn
                if mean > 0.5:
                    piece = chess.Piece.from_symbol('P')
                else:
                    piece = chess.Piece.from_symbol('p')
                board.set_piece_at(square_index, piece)
                confidences.append(1.0)
            else:
                confidences.append(0.0)
    confidence = sum(confidences) / len(confidences)
    return board, confidence >= empty_threshold

def image_to_board(img, templates_dir=None):
    """
    High-level: detect board, warp, split, and try to recognize pieces.
    Returns (board: chess.Board or None, warped_img, success_flag, message)
    """
    contour = find_board_contour(img)
    if contour is None:
        return None, None, False, "Board contour not found"
    warped, M = warp_board(img, contour, size=800)
    cells = split_cells(warped)
    templates = load_templates(templates_dir or "templates")
    if templates:
        board, ok = recognize_with_templates(cells, templates)
        if board:
            return board, warped, True, "Recognized via templates"
    # fallback
    board, ok = heuristic_detect_pieces(cells)
    if ok:
        return board, warped, True, "Recognized via heuristic (low confidence)"
    else:
        return None, warped, False, "Recognition uncertain; request manual correction"
