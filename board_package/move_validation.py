from .move_generation import (
    rook_moves,
    bishop_moves,
    queen_moves
)

def pawn_validity(board, sq_from, sq_to, clr):
    occ = board.occupied

    direction = -8 if clr else 8
    start_rank = 6 if clr else 1

    r1, f1 = divmod(sq_from, 8)
    f2 = sq_to % 8

    target = 1 << sq_to

    # forward move
    if f1 == f2:
        if sq_to == sq_from + direction and not (target & occ):
            return True

        if r1 == start_rank and sq_to == sq_from + 2 * direction:
            mid = sq_from + direction
            if not ((1 << mid) & occ) and not (target & occ):
                return True

    # capture
    if abs(f1 - f2) == 1 and abs(sq_to - sq_from) in (9, 7):
        enemy = board.black if clr else board.white
        if target & enemy:
            return True
        elif not (target & enemy) and board.en_passant_square  == sq_to:
            return True

    return False

def knight_validity(board, sq_from, sq_to, clr):
    own = board.white if clr else board.black

    r1, f1 = divmod(sq_from, 8)
    r2, f2 = divmod(sq_to, 8)

    if (abs(r1 - r2), abs(f1 - f2)) not in [(2,1),(1,2)]:
        return False

    return not ((1 << sq_to) & own)

def bishop_validity(board, sq_from, sq_to, clr):
    enemy = board.black if clr else board.white

    moves = bishop_moves(sq_from, enemy, False)
    return bool(moves & (1 << sq_to))

def rook_validity(board, sq_from, sq_to, clr):
    enemy = board.black if clr else board.white

    moves = rook_moves(sq_from, enemy, False)
    return bool(moves & (1 << sq_to))

def queen_validity(board, sq_from, sq_to, clr):
    enemy = board.black if clr else board.white

    moves = queen_moves(sq_from, enemy, False)
    return bool(moves & (1 << sq_to))

def king_validity(board, sq_from, sq_to, clr):
    own = board.white if clr else board.black

    r1, f1 = divmod(sq_from, 8)
    r2, f2 = divmod(sq_to, 8)


    if (abs(r1 - r2), abs(f1 - f2)) not in [(1,1),(1,0),(0,1)]:
        return False
    
    if ((1 << sq_to) & own): return False

    return True

def check_validity_sq(board, sq_from, sq_to):
    piece = board.get_piece(sq_from)
    if piece == ".":
        return False

    clr = piece.isupper()
    if clr != board.white_to_move:
        return False
    if piece.lower() == "p":
        return pawn_validity(sq_from, sq_to, clr)
    if piece.lower() == "n":
        return knight_validity(sq_from, sq_to, clr)
    if piece.lower() == "b":
        return bishop_validity(sq_from, sq_to, clr)
    if piece.lower() == "r":
        return rook_validity(sq_from, sq_to, clr)
    if piece.lower() == "q":
        return queen_validity(sq_from, sq_to, clr)
    if piece.lower() == "k":
        return king_validity(sq_from, sq_to, clr)

    return False