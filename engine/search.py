import time

from .constants import (
    INF,
    MAX_PLY,
    Q_DELTA_MARGIN,
    EXACT,
    LOWERBOUND,
    UPPERBOUND
)

from .evaluation import (
    piece_values,
    evaluate
)

from .move_ordering import MoveOrdering
from .transposition import TranspositionTable

from board_package.move_generation import (
    generate_legal_moves,
    generate_captures,
    generate_pseudo_moves
)
from board_package.move_execution import (
    makeMove_sq,
    unmakeMove_sq,
    make_null_move,
    unmake_null_move
)
from board_package.attacks import (
    is_discovered_check,
    is_king_attacked,
    gives_check
)

class Engine:

    def __init__(self, board):
        self.board = board
        self.nodes = 0
        self.qnodes = 0
        self.root_ply = 0
        self.move_ordering = MoveOrdering()
        self.tt = TranspositionTable()
    
    def quiescence(self, alpha, beta, maximizing, in_check=None, qply=0):
        if in_check == None:
            in_check = is_king_attacked(self.board, maximizing)
        stand_pat = evaluate(self.board)

        self.qnodes += 1

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

            moves = generate_captures(self.board, maximizing)

        else:
            # search evasions when in check to avoid illegal moves
            moves = generate_legal_moves(self.board, maximizing, in_check=True)

        for sq_from, sq_to in moves:

            piece = self.board.get_piece(sq_from)
            captured_piece = self.board.get_piece(sq_to)
            captured_value = abs(piece_values[captured_piece]) if captured_piece != "." else 0

            if maximizing:
                if stand_pat + captured_value + Q_DELTA_MARGIN < alpha:
                    continue
            else:
                if stand_pat - captured_value - Q_DELTA_MARGIN > beta:
                    continue

            makeMove_sq(self.board, sq_from, sq_to)

            # checks if making the move leaves king exposed to be captured in opposing turn
            if is_discovered_check(self.board, sq_from, sq_to, not maximizing, piece):
                unmakeMove_sq(self.board, sq_from, sq_to)
                continue

            gives_check_var = gives_check(self.board, maximizing, sq_from, sq_to)

            score = self.quiescence(alpha, beta, not maximizing, gives_check_var, qply + 1)

            unmakeMove_sq(self.board, sq_from, sq_to)

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
            entry = self.tt.probe(key)
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

        king_in_check = in_check if in_check != None else is_king_attacked(board, clr)

        # null move
        
        R = 2 if depth < 6 else 3 # null move depth reduction
        T = 3 # null move depth threshold
        pieceless = ((board.wp | board.bp | board.wk | board.bk) == board.occupied)
        # pieceless variable makes sure null move pruning doesnt occur in king pawn endgames
        # where tactical moves could be missed and zugzwang could yield false results when pruning

        if depth >= T and not king_in_check and not in_null_move and not pieceless:
            ep = make_null_move(board) # a way to pass en passant square into unmake_null_move
            if maximizing:
                score = self.alpha_beta(depth - 1 - R, beta - 1, beta, False, ply + 1, True, False)
                unmake_null_move(board, ep)
                if score >= beta:
                    return beta
            else:
                score = self.alpha_beta(depth - 1 - R, alpha, alpha + 1, True, ply + 1, True, False)
                unmake_null_move(board, ep)
                if score <= alpha:
                    return alpha
        
        # move generation

        moves = generate_pseudo_moves(board, clr) if not king_in_check else generate_legal_moves(board, clr, in_check= True)
        self.root_ply = ply
        moves.sort(key=lambda move: self.move_ordering.move_score(board, self.root_ply, move), reverse=True)

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

                makeMove_sq(board, sq_from, sq_to)

                if is_discovered_check(board, sq_from, sq_to, not clr, piece):
                    unmakeMove_sq(board, sq_from, sq_to)
                    continue

                gives_check_var = gives_check(board, clr, sq_from, sq_to)

                found_legal = True
                legal_index += 1
                # first legal move gets full-depth search
                if legal_index < 3 or depth < 3:
                    eval = self.alpha_beta(depth - 1, alpha, beta, False, ply + 1, in_check=gives_check_var)
                else:
                    reduction = 1
                    history = self.move_ordering.history_table[sq_from << 6 | sq_to] # << 6 is equal to *64
                    if history < 600:
                        reduction = 2
                    else:
                        reduction = 1

                    if captured_piece != ".": reduction = 0
                    eval = self.alpha_beta(depth - 1 - reduction, alpha, beta, False, ply + 1, in_check=gives_check_var)

                    # reduced move looks interesting -> full-depth re-search
                    if eval > alpha:
                        eval = self.alpha_beta(depth - 1, alpha, beta, False, ply + 1, in_check=gives_check_var)

                unmakeMove_sq(board, sq_from, sq_to)

                if eval > max_eval:
                    max_eval = eval
                    best_move = (sq_from, sq_to)
                alpha = max(alpha, eval)

                if beta <= alpha:
                    if self.board.get_piece(sq_to) == ".":   # quiet move
                        killers = self.move_ordering.killer_moves[ply]
                        # update history heuristics
                        self.move_ordering.update_history(sq_from, sq_to, depth)
                        
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

                self.tt.store(key, (depth, eval, EXACT, None))
                return eval

            if max_eval <= alpha_orig:
                flag = UPPERBOUND
            elif max_eval >= beta_orig:
                flag = LOWERBOUND
            else:
                flag = EXACT

            self.tt.store(key, (depth, max_eval, flag, best_move))
            return max_eval
        else:

            min_eval = INF
            best_move = None
            legal_index = 0
            for _, (sq_from, sq_to) in enumerate(moves):
                piece = board.get_piece(sq_from)
                captured_piece = board.get_piece(sq_to)

                makeMove_sq(board, sq_from, sq_to)
                
                if is_discovered_check(board, sq_from, sq_to, not clr, piece):
                    unmakeMove_sq(board, sq_from, sq_to)
                    continue

                gives_check_var = gives_check(board, clr, sq_from, sq_to)

                found_legal = True
                legal_index += 1
                # first legal move gets full-depth search
                if legal_index < 3 or depth < 3:
                    eval = self.alpha_beta(depth - 1, alpha, beta, True, ply + 1, in_check=gives_check_var)
                else:
                    reduction = 1
                    history = self.move_ordering.history_table[sq_from << 6 | sq_to] # << 6 is equal to *64
                    if history < 600:
                        reduction = 2
                    else:
                        reduction = 1

                    if captured_piece != ".": reduction = 0
                    eval = self.alpha_beta(depth - 1 - reduction, alpha, beta, True, ply + 1, in_check=gives_check_var)

                    # reduced move looks interesting -> full-depth re-search
                    if eval < beta:
                        eval = self.alpha_beta(depth - 1, alpha, beta, True, ply + 1, in_check=gives_check_var)

                unmakeMove_sq(board, sq_from, sq_to)

                if eval < min_eval:
                    min_eval = eval
                    best_move = (sq_from, sq_to)
                beta = min(beta, eval)

                if beta <= alpha:
                    if self.board.get_piece(sq_to) == ".":   # quiet move
                        killers = self.move_ordering.killer_moves[ply]
                        # update history heuristics
                        self.move_ordering.update_history(sq_from, sq_to, depth)
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

                self.tt.store(key, (depth, eval, EXACT, None))
                return eval
            
            if min_eval <= alpha_orig:
                flag = UPPERBOUND
            elif min_eval >= beta_orig:
                flag = LOWERBOUND
            else:
                flag = EXACT

            self.tt.store(key, (depth, min_eval, flag, best_move))
            return min_eval

    def find_best_move(self, max_depth):
        best_move = None
        best_eval = 0

        start_time = time.perf_counter()

        for depth in range(1, max_depth + 1):
            print("Entering depth: ", depth)
            move, eval = self.root_search(depth)

            best_move = move
            best_eval = eval

            if abs(best_eval) >= INF - MAX_PLY:
                print(f"Forced mate detected at depth {depth}")
                break

            # Halve history table between iterative deepening loops
            self.move_ordering.history_table = [val // 2 for val in self.move_ordering.history_table]
        for ply in range(MAX_PLY):
            self.move_ordering.killer_moves[ply][0] = None
            self.move_ordering.killer_moves[ply][1] = None


        elapsed = time.perf_counter() - start_time
        print("Move:", f"{best_move} calculated in: ", f"{elapsed:.3f} seconds")
        print("Nodes: ", self.nodes)
        nps = self.nodes / elapsed
        print(f"NPS: {nps:,.0f}")

        self.board.principal_variation.append(best_move)
        print(self.board.principal_variation)

        return best_move
        
    def root_search(self, depth):
        board = self.board

        best_move = None
        best_eval = -INF if board.white_to_move else INF

        moves = generate_legal_moves(board, board.white_to_move)
        self.root_ply = depth
        moves.sort(key=lambda move: self.move_ordering.move_score(board, self.root_ply, move), reverse=True)
        for sq_from, sq_to in moves:
            makeMove_sq(board, sq_from, sq_to)

            eval = self.alpha_beta(depth - 1, -INF, INF, board.white_to_move, 0)

            unmakeMove_sq(board, sq_from, sq_to)

            if board.white_to_move:
                if eval > best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

            else:
                if eval < best_eval:
                    best_eval = eval
                    best_move = (sq_from, sq_to)

        return (best_move, best_eval)