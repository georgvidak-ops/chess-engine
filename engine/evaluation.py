from .constants import (MAX_PLY, MOVEMENT, CAPTURE, PROMOTION)

piece_values = {
    "P": 100,
    "N": 320,
    "B": 330,
    "R": 500,
    "Q": 900,
    "K": 0,
    "p": -100,
    "n": -320,
    "b": -330,
    "r": -500,
    "q": -900,
    "k": 0
}

SEE_values = { # SEE is not implemented yet, but was supposed to be when I added this table
"P": 100,
"N": 320,
"B": 330,
"R": 500,
"Q": 900,
"K": 20000,
}

killer_moves = [
    [None, None]
    for _ in range(MAX_PLY)
]

# -------------------------
# Piece Square Tables
# -------------------------

PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    10, 10, 10, 10, 10, 10, 10, 10,
    15, 15, 20, 25, 25, 20, 15, 15,
    20, 20, 25, 35, 35, 25, 20, 20,
    25, 25, 30, 40, 40, 30, 25, 25,
    30, 30, 35, 45, 45, 35, 30, 30,
    35, 35, 40, 50, 50, 40, 35, 35,
    0,  0,  0,  0,  0,  0,  0,  0,
]
KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]
BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]
ROOK_TABLE = [
    0,  0,  5, 10, 10,  5,  0,  0,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    5, 10, 10, 10, 10, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]
QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]
KING_TABLE = [
    20, 30, 10,  0,  0, 10, 30, 20,
    20, 20,  0,  0,  0,  0, 20, 20,
    -10,-20,-20,-20,-20,-20,-20,-10,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30
]

PST = {
    "P": PAWN_TABLE,
    "N": KNIGHT_TABLE,
    "B": BISHOP_TABLE,
    "R": ROOK_TABLE,
    "Q": QUEEN_TABLE,
    "K": KING_TABLE,
}

def castling_rights_penalty(board):
    pen = 0
    cr = board.castling_rights

    wk = board.wk
    bk = board.bk

    white_castled = wk & ((1 << 62) | (1 << 58))  # g1 or c1
    black_castled = bk & ((1 << 6) | (1 << 2))    # g8 or c8

    masks = {
        0b1000: -15,  # white short
        0b0100: -10,  # white long
        0b0010: 15,   # black short
        0b0001: 10    # black long
    }

    for mask, penalty in masks.items():
        if not (cr & mask):
            # only penalize missing rights if king didn't actually castle that side
            if mask in (0b1000, 0b0100):  # white
                if not white_castled:
                    pen += 2 * penalty
            else:  # black
                if not black_castled:
                    pen += 2 * penalty
    return pen

def shift_eval(clr, type, move=None, piece=None): # if the move is a capture, arguement "piece" is captured piece
    pure_eval = 0
    sq_from, sq_to = 0, 0
    if move: sq_from, sq_to = move
    
    piece = piece.upper()

    if type == MOVEMENT:
        pure_eval -= PST[piece][sq_from]
        pure_eval += PST[piece][sq_to]
    elif type == CAPTURE:
        pure_eval += piece_values[piece] # + sign because the side playing is benefited by the amount of points lost on the enemy
    elif type == PROMOTION:
        pure_eval -= piece_values["P"]
        pure_eval += piece_values["Q"]

    return pure_eval if clr else -pure_eval

def evaluate(board):
    return board.eval_score + castling_rights_penalty(board)