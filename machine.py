import time

INF = 999_999_999
MAX_PLY = 64
Q_DELTA_MARGIN = 100

# move_score universal values
CAPTURE_MOVE_VALUE = 100_000
KILLER_MOVE_1_SCORE = 90_000
KILLER_MOVE_2_SCORE = 80_000
MAX_QUIET_MOVE_SCORE = 50_000

# tt flags
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

# eval shift types
MOVEMENT = 0
CAPTURE = 1
PROMOTION = 2
# en passant and castling are both variants of movement and capture types

class Machine:

    def __init__(self, board):
        self.board = board
        self.nodes = 0
        self.tt = {}
        self.root_ply = 0
        self.history_table = [0] * 4096 # instead of a 64x64 value 2d table a 1d table of 64*64 elements computes faster

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

    def move_score(self, move):
        sq_from, sq_to = move
        ply = self.root_ply

        attacker = self.board.get_piece(sq_from)
        target = self.board.get_piece(sq_to)
        
        # 1. Killer moves
        killer1, killer2 = self.killer_moves[ply]
        if move == killer1:
            return KILLER_MOVE_1_SCORE
        if move == killer2:
            return  KILLER_MOVE_2_SCORE
        # 2. Ordered captures
        if target != ".":
            return CAPTURE_MOVE_VALUE + (10 * abs(self.piece_values[target]) - abs(self.piece_values[attacker]))

        return self.history_table[(sq_from << 6) | sq_to]
    
    def castling_rights_penalty(self):
        pen = 0
        cr = self.board.castling_rights

        wk = self.board.wk
        bk = self.board.bk

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

    def shift_eval(self, clr, type, move=None, piece=None): # if the move is a capture, arguement "piece" is captured piece
        pure_eval = 0
        sq_from, sq_to = 0, 0
        if move: sq_from, sq_to = move
        
        piece = piece.upper()

        if type == MOVEMENT:
            pure_eval -= self.PST[piece][sq_from]
            pure_eval += self.PST[piece][sq_to]
        elif type == CAPTURE:
            pure_eval += self.piece_values[piece] # + sign because the side playing is benefited by the amount of points lost on the enemy
        elif type == PROMOTION:
            pure_eval -= self.piece_values["P"]
            pure_eval += self.piece_values["Q"]

        return pure_eval if clr else -pure_eval

    def evaluate(self):
        return self.board.eval_score + self.castling_rights_penalty()
    
    def quiescence(self, alpha, beta, maximizing, in_check=None):
        if in_check == None:
            in_check = self.board.is_king_attacked(maximizing)
        stand_pat = self.evaluate()

        if not in_check:
            if maximizing:
                if stand_pat >= beta:
                    return beta
                if stand_pat > alpha:
                    alpha = stand_pat
            else:
                if stand_pat <= alpha:
                    return alpha
                if stand_pat < beta:
                    beta = stand_pat

            moves = self.board.generate_captures(maximizing)

        else:
            # search evasions when in check to avoid illegal moves
            moves = self.board.generate_legal_moves(maximizing, in_check=True)

        for sq_from, sq_to in moves:

            piece = self.board.get_piece(sq_from)
            captured_piece = self.board.get_piece(sq_to)
            captured_value = abs(self.piece_values[captured_piece]) if captured_piece != "." else 0

            if maximizing:
                if stand_pat + captured_value + Q_DELTA_MARGIN < alpha:
                    continue
            else:
                if stand_pat - captured_value - Q_DELTA_MARGIN > beta:
                    continue

            self.board.makeMove_sq(sq_from, sq_to)

            # checks if making the move leaves king exposed to be captured in opposing turn
            if self.board.is_discovered_check(sq_from, sq_to, not maximizing, piece):
                self.board.unmakeMove_sq(sq_from, sq_to)
                continue

            gives_check = self.board.gives_check(maximizing, sq_from, sq_to)

            score = self.quiescence(alpha, beta, not maximizing, gives_check)

            self.board.unmakeMove_sq(sq_from, sq_to)

            if maximizing:
                if score > alpha:
                    alpha = score
                if alpha >= beta:
                    return beta
            else:
                if score < beta:
                    beta = score
                if beta <= alpha:
                    return alpha
                
        return alpha if maximizing else beta
    
    def alpha_beta(self, depth, alpha, beta, maximizing, ply, in_null_move=False, in_check=None): # in_check tuple (1: is the argument passed over?, 2: is the king in check?)
        board = self.board

        self.nodes += 1

        alpha_orig = alpha
        beta_orig = beta

        key = board.hash

        if not in_null_move:
            entry = self.tt.get(key)
        else:
            entry = None

        stored_move = None

        if entry is not None:
            stored_depth, stored_score, stored_flag, stored_move = entry

            if stored_depth >= depth:

                if stored_flag == EXACT:
                    return stored_score

                elif stored_flag == LOWERBOUND:
                    alpha = max(alpha, stored_score)

                elif stored_flag == UPPERBOUND:
                    beta = min(beta, stored_score)

                if alpha >= beta:
                    return stored_score

        if depth <= 0:
            return self.quiescence(alpha, beta, maximizing)
        
        clr = board.white_to_move

        king_in_check = in_check if in_check != None else board.is_king_attacked(clr)

        # null move
        
        R = 2 if depth < 6 else 3 # null move depth reduction
        T = 3 # null move depth threshold
        pieceless = ((board.wp | board.bp | board.wk | board.bk) == board.occupied)
        # pieceless variable makes sure null move pruning doesnt occur in king pawn endgames
        # where tactical moves could be missed and zugzwang could yield false results when pruning

        if depth >= T and not king_in_check and not in_null_move and not pieceless:
            ep = board.make_null_move() # a way to pass en passant square into unmake_null_move
            if maximizing:
                score = self.alpha_beta(depth - 1 - R, beta - 1, beta, False, ply + 1, True, False)
                board.unmake_null_move(ep)
                if score >= beta:
                    return beta
            else:
                score = self.alpha_beta(depth - 1 - R, alpha, alpha + 1, True, ply + 1, True, False)
                board.unmake_null_move(ep)
                if score <= alpha:
                    return alpha
        
        # move generation

        moves = board.generate_pseudo_moves(clr) if not king_in_check else board.generate_legal_moves(clr, in_check= True)
        self.root_ply = ply
        moves.sort(key = self.move_score, reverse = True)

        tt_moves = 0

        if stored_move in moves:
            tt_moves += 1
            moves.remove(stored_move)
            moves.insert(0, stored_move)
        
        found_legal = False
        
        if maximizing:

            max_eval = -INF
            best_move = None
            legal_index = 0
            for _, (sq_from, sq_to) in enumerate(moves):
                piece = board.get_piece(sq_from)
                captured_piece = board.get_piece(sq_to)

                board.makeMove_sq(sq_from, sq_to)

                if board.is_discovered_check(sq_from, sq_to, not clr, piece):
                    board.unmakeMove_sq(sq_from, sq_to)
                    continue

                gives_check = board.gives_check(clr, sq_from, sq_to)

                found_legal = True
                legal_index += 1
                # first legal move gets full-depth search
                if legal_index < 3 or depth < 3:
                    eval = self.alpha_beta(depth - 1, alpha, beta, False, ply + 1, in_check=gives_check)
                else:
                    reduction = 1
                    history = self.history_table[sq_from << 6 | sq_to] # << 6 is equal to *64
                    if history < 600:
                        reduction = 2
                    else:
                        reduction = 1

                    if captured_piece != ".": reduction = 0
                    eval = self.alpha_beta(depth - 1 - reduction, alpha, beta, False, ply + 1, in_check=gives_check)

                    # reduced move looks interesting -> full-depth re-search
                    if eval > alpha:
                        eval = self.alpha_beta(depth - 1, alpha, beta, False, ply + 1, in_check=gives_check)

                board.unmakeMove_sq(sq_from, sq_to)

                if eval > max_eval:
                    max_eval = eval
                    best_move = (sq_from, sq_to)
                alpha = max(alpha, eval)

                if beta <= alpha:
                    if self.board.get_piece(sq_to) == ".":   # quiet move
                        killers = self.killer_moves[ply]
                        # update history heuristics
                        idx = (sq_from << 6) | sq_to
                        self.history_table[idx] = min(self.history_table[idx] + (depth * depth) * 12, MAX_QUIET_MOVE_SCORE)

                        # update killer moves
                        if killers[0] != (sq_from, sq_to):
                            killers[1] = killers[0]
                            killers[0] = (sq_from, sq_to)
                    break

            # no legal moves
            if not found_legal:
                if king_in_check:
                    eval = (-INF + ply) if maximizing else (INF - ply)
                else:
                    eval = 0 # stalemate

                self.tt[key] = (depth, eval, EXACT, None)
                return eval

            if max_eval <= alpha_orig:
                flag = UPPERBOUND
            elif max_eval >= beta_orig:
                flag = LOWERBOUND
            else:
                flag = EXACT

            self.tt[key] = (depth, max_eval, flag, best_move)
            return max_eval
        else:

            min_eval = INF
            best_move = None
            legal_index = 0
            for _, (sq_from, sq_to) in enumerate(moves):
                piece = board.get_piece(sq_from)
                captured_piece = board.get_piece(sq_to)

                board.makeMove_sq(sq_from, sq_to)
                
                if board.is_discovered_check(sq_from, sq_to, not clr, piece):
                    board.unmakeMove_sq(sq_from, sq_to)
                    continue

                gives_check = board.gives_check(clr, sq_from, sq_to)

                found_legal = True
                legal_index += 1
                # first legal move gets full-depth search
                if legal_index < 3 or depth < 3:
                    eval = self.alpha_beta(depth - 1, alpha, beta, True, ply + 1, in_check=gives_check)
                else:
                    reduction = 1
                    history = self.history_table[sq_from << 6 | sq_to] # << 6 is equal to *64
                    if history < 600:
                        reduction = 2
                    else:
                        reduction = 1

                    if captured_piece != ".": reduction = 0
                    eval = self.alpha_beta(depth - 1 - reduction, alpha, beta, True, ply + 1, in_check=gives_check)

                    # reduced move looks interesting -> full-depth re-search
                    if eval < beta:
                        eval = self.alpha_beta(depth - 1, alpha, beta, True, ply + 1, in_check=gives_check)

                board.unmakeMove_sq(sq_from, sq_to)

                if eval < min_eval:
                    min_eval = eval
                    best_move = (sq_from, sq_to)
                beta = min(beta, eval)

                if beta <= alpha:
                    if self.board.get_piece(sq_to) == ".":   # quiet move
                        killers = self.killer_moves[ply]
                        # update history heuristics
                        idx = (sq_from << 6) | sq_to
                        self.history_table[idx] = min(self.history_table[idx] + (depth * depth) * 12, MAX_QUIET_MOVE_SCORE)
                        # update killer moves
                        if killers[0] != (sq_from, sq_to):
                            killers[1] = killers[0]
                            killers[0] = (sq_from, sq_to)
                        
                    break

            # no legal moves
            if not found_legal:
                if king_in_check:
                    eval = (-INF + ply) if maximizing else (INF - ply)
                else:
                    eval = 0 # stalemate

                self.tt[key] = (depth, eval, EXACT, None)
                return eval
            
            if min_eval <= alpha_orig:
                flag = UPPERBOUND
            elif min_eval >= beta_orig:
                flag = LOWERBOUND
            else:
                flag = EXACT

            self.tt[key] = (depth, min_eval, flag, best_move)
            return min_eval

    def find_best_move(self, max_depth):
        best_move = None
        best_eval = 0

        start_time = time.perf_counter()

        for depth in range(1, max_depth + 1):
            move, eval = self.root_search(depth)

            best_move = move
            best_eval = eval

            if abs(best_eval) >= INF - MAX_PLY:
                print(f"Forced mate detected at depth {depth}")
                break

            # Halve history table between iterative deepening loops
            self.history_table = [val // 2 for val in self.history_table]
        for ply in range(MAX_PLY):
            self.killer_moves[ply][0] = None
            self.killer_moves[ply][1] = None


        elapsed = time.perf_counter() - start_time
        print("Move:", f"{best_move} calculated in: ", f"{elapsed:.3f} seconds")
        print("Nodes: ", self.nodes)
        nps = self.nodes / elapsed
        print(f"NPS: {nps:,.0f}")

        return best_move
        
    def root_search(self, depth):
        board = self.board

        best_move = None
        best_eval = -INF if board.white_to_move else INF

        moves = board.generate_legal_moves(board.white_to_move)
        self.root_ply = depth
        moves.sort(key = self.move_score, reverse = True)
        for sq_from, sq_to in moves:
            board.makeMove_sq(sq_from, sq_to)

            eval = self.alpha_beta(depth - 1, -INF, INF, board.white_to_move, 0)

            board.unmakeMove_sq(sq_from, sq_to)

            if board.white_to_move:
                if eval > best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

            else:
                if eval < best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

        return (best_move, best_eval)