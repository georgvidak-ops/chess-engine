from .constants import (MASK_64, DIAGONAL, STRAIGHT)
from .attacks import (
    raycast_attacks,
    pawn_attacks,
    pawn_attackers,
    knight_attacks,
    bishop_attacks,
    rook_attacks,
    queen_attacks,
    king_attacker,
    is_king_attacked
)
from .move_execution import (
    makeMove_sq,
    unmakeMove_sq
)
from .attacks import is_discovered_check

def pawn_moves(board, from_sq, clr):
    occ = board.occupied
    moves = 0

    direction = -8 if clr else 8
    start_rank = range(48, 56) if clr else range(8, 16)

    # single push
    one_step = from_sq + direction

    if 0 <= one_step < 64:
        one_bit = 1 << one_step

        if not (one_bit & occ):
            moves |= one_bit

            # double push
            if from_sq in start_rank:
                two_step = from_sq + 2 * direction

                if 0 <= two_step < 64:
                    two_bit = 1 << two_step

                    if not (two_bit & occ):
                        moves |= two_bit

    # captures
    attacks = pawn_attacks(board, from_sq, clr)

    enemy = board.black if clr else board.white

    moves |= attacks & enemy

    # en passant
    if board.en_passant_square is not None:
        ep_bit = 1 << board.en_passant_square

        if attacks & ep_bit:
            moves |= ep_bit

    return moves & MASK_64

def bishop_moves(board, sq, enemy, raycasts): # raycasts = True tells the program to not count any object it hit whether its own or enemy piece
    return raycast_attacks(board, sq, DIAGONAL, enemy, raycasts)

def rook_moves(board, sq, enemy, raycasts): # raycasts = True tells the program to not count any object it hit whether its own or enemy piece
    return raycast_attacks(board, sq, STRAIGHT, enemy, raycasts)

def queen_moves(board, sq, enemy, raycasts): # raycasts = True tells the program to not count any object it hit whether its own or enemy piece
    return rook_moves(board, sq, enemy, raycasts) | bishop_moves(board, sq, enemy, raycasts)

def pseudo_move_castling(board, clr):
    pseudo_castles = []
    rights = board.castling_rights
    king = board.wk if clr else board.bk

    from_sq = 60 if clr else 4
    to_sq_short = 62 if clr else 6
    to_sq_long  = 58 if clr else 2

    if rights == 0b0000 or not (king & (1 << from_sq)):
        return pseudo_castles

    pieces_short = [61, 62] if clr else [5, 6]
    pieces_long  = [57, 58, 59] if clr else [1, 2, 3]

    can_s = all(not ((1 << sq) & board.occupied) for sq in pieces_short)
    can_l = all(not ((1 << sq) & board.occupied) for sq in pieces_long)

    mask_s = 0b1000 if clr else 0b0010
    mask_l = 0b0100 if clr else 0b0001

    enemy_attacks = (
        pawn_attacks(board, None, not clr)
        | knight_attacks(board, None, not clr)
        | bishop_attacks(board, None, not clr)
        | rook_attacks(board, None, not clr)
        | queen_attacks(board, None, not clr)
        | king_attacker(board, not clr)
    )

    if clr:
        safe_short = not (enemy_attacks & ((1 << 60) | (1 << 61) | (1 << 62)))
        safe_long  = not (enemy_attacks & ((1 << 60) | (1 << 59) | (1 << 58)))
    else:
        safe_short = not (enemy_attacks & ((1 << 4) | (1 << 5) | (1 << 6)))
        safe_long  = not (enemy_attacks & ((1 << 4) | (1 << 3) | (1 << 2)))

    if can_s and (board.castling_rights & mask_s) and safe_short:
        pseudo_castles.append((from_sq, to_sq_short))

    if can_l and (board.castling_rights & mask_l) and safe_long:
        pseudo_castles.append((from_sq, to_sq_long))

    return pseudo_castles

def legal_move_castling(board, clr):
    pseudo_castles = pseudo_move_castling(board, clr)
    legal_castles = []

    for sq_from, sq_to in pseudo_castles:
        makeMove_sq(board, sq_from, sq_to, castleLegalityChecking=True)
        
        if not is_king_attacked(board, clr):
            legal_castles.append((sq_from, sq_to))

        unmakeMove_sq(board, sq_from, sq_to, castleLegalityChecking=True)

    return legal_castles


def generate_pseudo_moves(board, clr):
    pseudo_moves = []
    own = board.white if clr else board.black
    enemy = board.black if clr else board.white

    pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

    for piece in pieces:
        bb = getattr(board, piece)

        while bb:
            from_bit = bb & -bb
            from_sq = from_bit.bit_length() - 1
            bb &= bb - 1  # remove LSB

            # generate pseudo-legal targets for this square
            if piece == "wp" or piece == "bp":
                moves = pawn_moves(board, from_sq, clr)
            elif piece == "wn" or piece == "bn":
                moves = knight_attacks(board, from_sq, clr) & ~own
            elif piece == "wb" or piece == "bb":
                moves = bishop_moves(board, from_sq, enemy, False)
            elif piece == "wr" or piece == "br":
                moves = rook_moves(board, from_sq, enemy, False)
            elif piece == "wq" or piece == "bq":
                moves = queen_moves(board, from_sq, enemy, False)
            else:  # king
                moves = king_attacker(board, clr) & ~own

            # iterate targets
            while moves:
                to_bit = moves & -moves
                to_sq = to_bit.bit_length() - 1
                moves &= moves - 1

                pseudo_moves.append((from_sq, to_sq))

    return pseudo_moves + pseudo_move_castling(board, clr)

def generate_legal_moves(board, clr, in_check=False):
    legal_moves = []
    own = board.white if clr else board.black
    enemy = board.black if clr else board.white

    pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

    for piece in pieces:
        bb = getattr(board, piece)

        while bb:
            from_bit = bb & -bb
            from_sq = from_bit.bit_length() - 1
            bb &= bb - 1  # remove LSB

            # generate pseudo-legal targets for this square
            if piece[1] == "p":
                moves = pawn_moves(board, from_sq, clr)
            elif piece[1] == "n":
                moves = knight_attacks(board, from_sq, clr) & ~own
            elif piece[1] == "b":
                moves = bishop_moves(board, from_sq, enemy, False)
            elif piece[1] == "r":
                moves = rook_moves(board, from_sq, enemy, False)
            elif piece[1] == "q":
                moves = queen_moves(board, from_sq, enemy, False)
            else:  # king
                moves = king_attacker(board, clr) & ~own
                

    # Had to repeat pseudo-legal generation because from_sq couldnt be passed as arguement without causing too much chaos


            # iterate targets
            while moves:
                to_bit = moves & -moves
                to_sq = to_bit.bit_length() - 1
                moves &= moves - 1

                # make move
                makeMove_sq(board, from_sq, to_sq)
                
                # legality check
                if in_check:
                    if not is_king_attacked(board, clr):
                        legal_moves.append((from_sq, to_sq))
                else:
                    piece_moved = board.get_piece(to_sq)
                    if not is_discovered_check(board, from_sq, to_sq, clr, piece_moved):
                        legal_moves.append((from_sq, to_sq))
                

                # undo move
                unmakeMove_sq(board, from_sq, to_sq)

    return legal_moves + legal_move_castling(board, clr)

def generate_captures(board, clr):
    legal_captures = []
    enemy = board.black if clr else board.white
    enemy_king = board.bk if clr else board.wk
    captures = []

    pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

    for piece in pieces:
        bb = getattr(board, piece)

        while bb:
            from_bit = bb & -bb
            from_sq = from_bit.bit_length() - 1
            bb &= bb - 1  # remove LSB

            # generate pseudo-legal targets for this square
            if piece[1] == "p":
                captures = pawn_attackers(from_sq, clr) & enemy
            elif piece[1] == "n":
                captures = knight_attacks(board, from_sq, clr) & enemy
            elif piece[1] == "b":
                captures = bishop_moves(board, from_sq, enemy, False) & enemy
            elif piece[1] == "r":
                captures = rook_moves(board, from_sq, enemy, False) & enemy
            elif piece[1] == "q":
                captures = queen_moves(board, from_sq, enemy, False) & enemy
            else:  # king
                captures = king_attacker(board, clr) & enemy    

            # iterate targets
            while captures:
                to_bit = captures & -captures
                if to_bit & enemy_king:
                    continue

                to_sq = to_bit.bit_length() - 1
                captures &= captures - 1

                # make move
                makeMove_sq(board, from_sq, to_sq)

                # legality check
                if not is_king_attacked(board, clr):
                    legal_captures.append((from_sq, to_sq))

                # undo move
                unmakeMove_sq(board, from_sq, to_sq)

    return legal_captures


def perft(self, depth, clr, root_depth=None):
    # If root_depth isn't set, initialize it to the starting depth
    if root_depth is None:
        root_depth = depth

    # reached leaf node
    if depth == 0:
        return 1

    nodes = 0

    # generate all legal moves
    legal_moves = generate_legal_moves(clr)

    # recurse through move tree
    for sq_from, sq_to in legal_moves:

        # make move
        makeMove_sq(sq_from, sq_to)
        # recurse and get count for this specific branch
        branch_nodes = self.perft(depth - 1, not clr, root_depth)
        nodes += branch_nodes

        # undo move
        unmakeMove_sq(sq_from, sq_to)

        # SPLIT/DIVIDE: If at the top-most level of the search, print the results for this move
        if depth == root_depth:
            move_str = f"{sq_from} -> {sq_to}" 
            print(f"{move_str}: {branch_nodes}")

    # Print summary line
    if depth == root_depth:
        print(f"\nTotal Nodes: {nodes}")

    return nodes
