INF = 999999

class Machine:

    def __init__(self, board):
        self.board = board
        self.tt = {}

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

        attacker = self.board.get_piece(sq_from)
        target = self.board.get_piece(sq_to)

        score = 0
        if target != ".":
            score += 10 * abs(self.piece_values[target]) - abs(self.piece_values[attacker])

        return score
    
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

    

    def evaluate(self):
        eval = 0
        eval += self.castling_rights_penalty()
        for sq in range(64):
            piece = self.board.get_piece(sq)

            if piece != ".":
                eval += self.piece_values[piece]
                if piece.isupper():
                    eval += self.PST[piece][sq]
                else:
                    eval -= self.PST[piece.upper()][63 - sq]

        return eval
    
    def quiescence(self, alpha, beta, maximizing):

        stand_pat = self.evaluate()

        if maximizing:
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)
        else:
            if stand_pat <= alpha:
                return alpha
            beta = min(beta, stand_pat)
        legal_moves = self.board.generate_legal_moves(maximizing)

        for sq_from, sq_to in legal_moves:
            if self.board.get_piece(sq_to) == ".":
                continue

            self.board.makeMove_sq(sq_from, sq_to)
            score = self.quiescence(alpha, beta, not maximizing)
            self.board.unmakeMove_sq(sq_from, sq_to)

            if maximizing:
                alpha = max(alpha, score)
                if alpha >= beta:
                    return beta
            else:
                beta = min(beta, score)
                if beta <= alpha:
                    return alpha
                
        return alpha if maximizing else beta
    
    def alpha_beta(self, depth, alpha, beta, maximizing):
        board = self.board

        key = board.hash

        entry = self.tt.get(key)

        if entry is not None:
            stored_depth, stored_score = entry

            if stored_depth >= depth:
                return stored_score

        if depth == 0:
            return self.quiescence(alpha, beta, maximizing)

        clr = maximizing
        legal_moves = board.generate_legal_moves(clr)
        legal_moves.sort(key = self.move_score, reverse = True)

        # no legal moves
        if not legal_moves:
            if board.king_in_check(clr):
                eval = (-INF + depth) if maximizing else (INF - depth)
            else:
                eval = 0 #stalemate

            self.tt[key] = (depth, eval)
            return eval
        
        if maximizing:

            max_eval = -INF
            for sq_from, sq_to in legal_moves:
                board.makeMove_sq(sq_from, sq_to)

                eval = self.alpha_beta(depth - 1, alpha, beta, False)
                board.unmakeMove_sq(sq_from, sq_to)

                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)

                if beta <= alpha:
                    break

            self.tt[key] = (depth, max_eval)
            return max_eval
        else:

            min_eval = INF
            for sq_from, sq_to in legal_moves:
                board.makeMove_sq(sq_from, sq_to)

                eval = self.alpha_beta(depth - 1, alpha, beta, True)
                board.unmakeMove_sq(sq_from, sq_to)

                min_eval = min(min_eval, eval)
                beta = min(beta, eval)

                if beta <= alpha:
                    break
            
            self.tt[key] = (depth, min_eval)
            return min_eval
        
    def find_best_move(self, depth):
        board = self.board
        best_move = None
        best_eval = -INF if board.white_to_move else INF

        legal_moves = board.generate_legal_moves(board.white_to_move)
        print(len(legal_moves))

        for sq_from, sq_to in legal_moves:

            board.makeMove_sq(sq_from, sq_to)
            eval = self.alpha_beta(depth - 1, -INF, INF, board.white_to_move)

            board.unmakeMove_sq(sq_from, sq_to)

            if board.white_to_move:
                if eval > best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

            else:
                if eval < best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)
        print(best_move)
        return best_move