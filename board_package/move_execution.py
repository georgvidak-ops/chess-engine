from .constants import (
    MASK_64,
    GLOBAL_MAPPING,
    MOVEMENT,
    CAPTURE,
    PROMOTION,
)

from engine.evaluation import shift_eval
from .castling import (
    castle,
    capture_castling_rights,
    castling_rights_modify,
)

from zobrist import Zobrist
zobrist = Zobrist()

def promotion(board, sq, making): # making == True means the program is making a move, False means unmaking
    clr = board.white_to_move if making else not board.white_to_move
    queen_bb = board.wq if clr else board.bq
    pawn_bb = board.wp if clr else board.bp
    if making:
        pawn_bb &= ~(1 << sq) & MASK_64
        queen_bb |= (1 << sq)
    else:
        queen_bb &= ~(1 << sq) & MASK_64
        pawn_bb |= (1 << sq)

    attr1, attr2 = ("wp", "wq") if clr else ("bp", "bq")
    setattr(board, attr1, pawn_bb)
    setattr(board, attr2, queen_bb)

    return True

# -------------------------
# MAKE MOVE
# -------------------------

def makeMove_sq(board, sq_from, sq_to, castleLegalityChecking=False):
    piece = board.get_piece(sq_from)

    old_en_passant_square = 0
    old_eval = board.eval_score

    if piece == ".":
        return False

    # castling
    if abs(sq_to - sq_from) == 2 and piece.lower() == "k" and not castleLegalityChecking:
        r_piece = "r" if piece == "k" else "R"
        # setting variables
        sq_from_rook, sq_to_rook = castle(sq_from, sq_to, True, board.white_to_move)
        to_bit = 1 << sq_to_rook
        from_bit = 1 << sq_from_rook
        # moving rook
        bb = getattr(board, GLOBAL_MAPPING[r_piece])
        bb &= ~from_bit & MASK_64
        bb |= to_bit
        setattr(board, GLOBAL_MAPPING[r_piece], bb)
        # shift eval
        board.eval_score += shift_eval(
            board.white_to_move, # clr
            MOVEMENT, # type
            move = (sq_from_rook, sq_to_rook), # move
            piece = r_piece
        )

        board.hash ^= zobrist.piece_keys[r_piece][sq_from_rook]
        board.hash ^= zobrist.piece_keys[r_piece][sq_to_rook]
    
    # remove old EP from hash
    if board.en_passant_square:
        board.hash ^= zobrist.ep_keys[board.en_passant_square % 8]

    old_en_passant_square = board.en_passant_square

    # update EP state
    if piece.lower() == "p" and abs(sq_to - sq_from) == 16:
        board.en_passant_square = (sq_from + sq_to) // 2
    else:
        board.en_passant_square = 0

    # add new EP to hash
    if board.en_passant_square:
        board.hash ^= zobrist.ep_keys[board.en_passant_square % 8]

    # handle EP
    was_en_passant = False
    if not ((1 << sq_to) & board.occupied) and piece.upper() == "P" and abs(sq_to - sq_from) in (7, 9) and sq_to == old_en_passant_square:
        #if these conditions are met then the move was a pawn that captured another via en passant
        was_en_passant = True

        #shift eval
        board.eval_score += shift_eval(
            board.white_to_move, # clr
            CAPTURE, # type
            piece = "P"
        )

        en_passant_capture_removal(board, sq_to, board.white_to_move)

    # remove old castling rights
    board.hash ^= zobrist.castling_keys[board.castling_rights]
    
    old_castling_rights = board.castling_rights
    castling_rights_modify(board, piece, sq_from)

    from_bit = 1 << sq_from
    to_bit = 1 << sq_to

    just_promoted = False

    captured_piece = "."
    if was_en_passant:
        captured_piece = "bp" if board.white_to_move else "wp"
        direction = 8 if board.white_to_move else - 8
        board.hash ^= zobrist.piece_keys[board.translate(captured_piece)][sq_to + direction]
    # capture removal
    for attr in [board.wp, board.wn, board.wb, board.wr, board.wq, board.wk, board.bp, board.bn, board.bb, board.br, board.bq, board.bk]:
        if attr & to_bit:
            captured_piece = board.translate(attr)

            if captured_piece == "wr" or captured_piece == "br":
                capture_castling_rights(board, sq_to)

            board.hash ^= zobrist.piece_keys[board.translate(captured_piece)][sq_to]
            setattr(board, captured_piece, getattr(board, captured_piece) & ~to_bit)

            # shift eval
            board.eval_score += shift_eval(
                board.white_to_move, # clr
                CAPTURE, # type
                piece = board.translate(captured_piece) # captured piece is passed as an argument instead of moved piece when move is a capture
            )


    # add new castling rights to hash
    board.hash ^= zobrist.castling_keys[board.castling_rights]
    
    # move piece

    board.hash ^= zobrist.piece_keys[piece][sq_from]
    board.hash ^= zobrist.piece_keys[piece][sq_to]

    bb = getattr(board, GLOBAL_MAPPING[piece])
    bb &= ~from_bit & MASK_64
    bb |= to_bit
    setattr(board, GLOBAL_MAPPING[piece], bb)

    # shift eval
    board.eval_score += shift_eval(
        board.white_to_move, # clr
        MOVEMENT, # type
        move = (sq_from, sq_to), # move
        piece = piece
    )

    # promotion
    if piece.lower() == "p" and sq_to // 8 in (0,7):
        just_promoted = True
        promotion(board, sq_to, True)
        board.hash ^= zobrist.piece_keys[piece][sq_to]
        queen = "Q" if piece == "P" else "q"
        board.hash ^= zobrist.piece_keys[queen][sq_to]

        # shift eval
        board.eval_score += shift_eval(
            board.white_to_move, # clr
            PROMOTION, # type
            piece = "P"
        )

    board.white_to_move = not board.white_to_move

    # move stacking in memory
    moved_piece = piece
    promotion_happened = just_promoted
    old_white_to_move_after = board.white_to_move

    move_state = (
        moved_piece,
        captured_piece,
        old_en_passant_square,
        was_en_passant,
        old_castling_rights,
        promotion_happened,
        old_white_to_move_after,
        old_eval
    )
    board.hash ^= zobrist.side_key # update side-to-move hash key
    board.move_stack.append(move_state)

    white = board.wp | board.wn | board.wb | board.wr | board.wq | board.wk
    black = board.bp | board.bn | board.bb | board.br | board.bq | board.bk
    board.white = white
    board.black = black
    board.occupied = white | black

    return True

def unmakeMove_sq(board, sq_from, sq_to, castleLegalityChecking=False): # sq_from and #sq_to refer to the original move's sq_from and sq_to
    moved_piece, old_en_passant_square, old_castling_rights, promotion_happened, old_white_to_move_after, old_eval = (0,0,0,0,0,0)
    captured_piece = "."
    was_en_passant = False

    # restore saved move state
    (
        moved_piece,
        captured_piece,
        old_en_passant_square,
        was_en_passant,
        old_castling_rights,
        promotion_happened,
        old_white_to_move_after,
        old_eval
    ) = board.move_stack.pop()

    # restoring eval
    board.eval_score = old_eval

    # restoring castle
    if abs(sq_to - sq_from) == 2 and moved_piece.lower() == "k" and not castleLegalityChecking:
        r_piece = "r" if moved_piece == "k" else "R"
        # setting variables
        sq_from_rook, sq_to_rook = castle(sq_from, sq_to, False, not board.white_to_move) # color inversed because during unmake_move, make_move has already given turn to other player
        to_bit = 1 << sq_to_rook
        from_bit = 1 << sq_from_rook
        # moving rook
        bb = getattr(board, GLOBAL_MAPPING[r_piece])
        bb &= ~from_bit & MASK_64
        bb |= to_bit
        setattr(board, GLOBAL_MAPPING[r_piece], bb)

        board.hash ^= zobrist.piece_keys[r_piece][sq_from_rook]
        board.hash ^= zobrist.piece_keys[r_piece][sq_to_rook]


    from_bit = 1 << sq_from
    to_bit = 1 << sq_to

    board.hash ^= zobrist.side_key

    board.hash ^= zobrist.piece_keys[moved_piece][sq_from]
    board.hash ^= zobrist.piece_keys[moved_piece][sq_to]
    if captured_piece != ".":
        if was_en_passant:
            direction = -8 if board.white_to_move else +8
            board.hash ^= zobrist.piece_keys[board.translate(captured_piece)][sq_to + direction]
        else:
            board.hash ^= zobrist.piece_keys[board.translate(captured_piece)][sq_to]
    
    board.hash ^= zobrist.castling_keys[board.castling_rights] # remove hashed rights of move
    board.hash ^= zobrist.castling_keys[old_castling_rights] # hash rights before move

    if board.en_passant_square:
        board.hash ^= zobrist.ep_keys[board.en_passant_square % 8] # remove hashed ep square of move
    if old_en_passant_square:
        board.hash ^= zobrist.ep_keys[old_en_passant_square % 8] # hash ep square before move
    

    # undo promotion
    if moved_piece.lower() == "p" and sq_to // 8 in (0,7) and promotion_happened:
        queen = "Q" if moved_piece == "P" else "q"
        board.hash ^= zobrist.piece_keys[queen][sq_to]
        board.hash ^= zobrist.piece_keys[moved_piece][sq_to]
        promotion(board, sq_to, False)

    # move piece back
    bb = getattr(board, GLOBAL_MAPPING[moved_piece])
    bb &= ~to_bit & MASK_64
    bb |= from_bit
    setattr(board, GLOBAL_MAPPING[moved_piece], bb)

    # restore captured piece
    if captured_piece != ".":
        if was_en_passant:
            en_passant_capture_restoration(board, sq_to, not board.white_to_move) # color inversed because during unmake_move, make_move has already given turn to other player
        else:
            cap_bb = getattr(board, captured_piece)

            cap_bb |= to_bit

            setattr(board, captured_piece, cap_bb)

    board.en_passant_square = old_en_passant_square

    board.castling_rights = old_castling_rights

    board.white_to_move = not old_white_to_move_after

    white = board.wp | board.wn | board.wb | board.wr | board.wq | board.wk
    black = board.bp | board.bn | board.bb | board.br | board.bq | board.bk
    board.white = white
    board.black = black
    board.occupied = white | black

    return True

def make_null_move(board):
    board.white_to_move = not board.white_to_move
    board.hash ^= zobrist.side_key

    if board.en_passant_square:
        board.hash ^= zobrist.ep_keys[board.en_passant_square % 8]
        ep = board.en_passant_square
        board.en_passant_square = 0
        return ep
    return False

def unmake_null_move(board, ep_sq):
    board.hash ^= zobrist.side_key
    board.white_to_move = not board.white_to_move

    if ep_sq:
        board.hash ^= zobrist.ep_keys[ep_sq % 8]
        board.en_passant_square = ep_sq

def en_passant_capture_removal(board, sq_to, clr):
    direction = 8 if clr else -8

    to_bit = 1 << (sq_to + direction)
    attr = "bp" if clr else "wp"
    if getattr(board, attr) & to_bit:
        setattr(board, attr, getattr(board,attr) & ~to_bit & MASK_64)

    return

def en_passant_capture_restoration(board, sq_to, clr):
    direction = 8 if clr else -8
    
    to_bit = 1 << (sq_to + direction)

    attr = "bp" if clr else "wp"
    setattr(board, attr, getattr(board,attr) | to_bit & MASK_64)

    return
            