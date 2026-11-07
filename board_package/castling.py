def check_castling(board, type, clr): #type --> True = short castle, False = long castle
    if type and clr and (0b1000 & board.castling_rights):
        return not ((board.occupied & (1 << 61)) or (board.occupied & (1 << 62)))
    elif not type and clr and (0b0100 & board.castling_rights):
        return not ((board.occupied & (1 << 59)) or (board.occupied & (1 << 58)) or (board.occupied & (1 << 57)))
    if type and not clr and (0b0010 & board.castling_rights):
        return not ((board.occupied & (1 << 5)) or (board.occupied & (1 << 6)))
    elif not type and not clr and (0b0001 & board.castling_rights):
        return not ((board.occupied & (1 << 1)) or (board.occupied & (1 << 2)) or (board.occupied & (1 << 3)))

def castling_rights_modify(board, piece, sq_from):
    if piece == "K":
        board.castling_rights &= ~0b1100
    elif piece == "k":
        board.castling_rights &= ~0b0011

    elif piece == "R":
        if sq_from == 63:
            board.castling_rights &= ~0b1000
        elif sq_from == 56:
            board.castling_rights &= ~0b0100

    elif piece == "r":
        if sq_from == 7:
            board.castling_rights &= ~0b0010
        elif sq_from == 0:
            board.castling_rights &= ~0b0001

def capture_castling_rights(board, sq):
    if sq == 63:
        board.castling_rights &= ~0b1000
    elif sq == 56:
        board.castling_rights &= ~0b0100
    elif sq == 7:
        board.castling_rights &= ~0b0010
    elif sq == 0:
        board.castling_rights &= ~0b0001
    

def castle_rook_squares(sq_from, sq_to, clr):
    if sq_from == 60 and sq_to == 62 and clr:      # White O-O
        return 63, 61
    elif sq_from == 60 and sq_to == 58 and clr:    # White O-O-O
        return 56, 59
    elif sq_from == 4 and sq_to == 6 and not clr:      # Black O-O
        return 7, 5
    elif sq_from == 4 and sq_to == 2 and not clr:      # Black O-O-O
        return 0, 3

    return None

def castle(sq_from, sq_to, making, clr):
    r = castle_rook_squares(sq_from, sq_to, clr)

    from_sq, to_sq = (0,0)
    if making:
        from_sq, to_sq = r
    else:
        to_sq, from_sq = r

    return from_sq, to_sq