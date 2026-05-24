INF = 999999

class Machine:

    def __init__(self, board):
        self.board = board

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

    def evaluate(self):
        eval = 0
        for sq in range(64):
            piece = self.board.get_piece(sq)

            if piece != ".":
                eval += self.piece_values[piece]

        return eval
    
    def alpha_beta(self, depth, alpha, beta, maximizing):
        board = self.board
        if depth == 0:
            return self.evaluate()

        clr = maximizing
        legal_moves = board.generate_legal_moves(clr)

        # no legal moves
        if not legal_moves:
            if board.king_in_check(clr):
                return -INF if clr else INF
            return 0  # stalemate
        
        if maximizing:

            max_eval = -INF
            for sq_from, sq_to in legal_moves:
                board.makeMove_sq(sq_from, sq_to, False)

                eval = self.alpha_beta(depth - 1, alpha, beta, False)
                board.unmakeMove_sq(sq_from, sq_to, False)

                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)

                if beta <= alpha:
                    break

            return max_eval
        else:

            min_eval = INF
            for sq_from, sq_to in legal_moves:
                board.makeMove_sq(sq_from, sq_to, False)

                eval = self.alpha_beta(depth - 1, alpha, beta, True)
                board.unmakeMove_sq(sq_from, sq_to, False)

                min_eval = min(min_eval, eval)
                beta = min(beta, eval)

                if beta <= alpha:
                    break

            return min_eval
        
    def find_best_move(self, depth):
        board = self.board
        best_move = None
        best_eval = -INF if board.white_to_move else INF

        legal_moves = board.generate_legal_moves(board.white_to_move)

        for sq_from, sq_to in legal_moves:

            board.makeMove_sq(sq_from, sq_to, False)
            eval = self.alpha_beta(depth - 1, -INF, INF, not board.white_to_move)

            board.unmakeMove_sq(sq_from, sq_to, False)

            if board.white_to_move:
                if eval > best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

            else:
                if eval < best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

        return best_move