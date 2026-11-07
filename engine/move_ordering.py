from .constants import (
    MAX_PLY,
    CAPTURE_MOVE_VALUE,
    KILLER_MOVE_1_SCORE,
    KILLER_MOVE_2_SCORE,
    MAX_QUIET_MOVE_SCORE,
)
from .evaluation import piece_values

class MoveOrdering:

    def __init__(self):
        self.history_table = [0] * 4096 # instead of a 64x64 value 2d table a 1d table of 64*64 elements computes faster
        self.killer_moves = [[None, None] for _ in range(MAX_PLY)]

    def move_score(self, board, root_ply, move):
        sq_from, sq_to = move
        ply = root_ply

        attacker = board.get_piece(sq_from)
        target = board.get_piece(sq_to)
        
        # 1. Killer moves
        killer1, killer2 = self.killer_moves[ply]
        if move == killer1:
            return KILLER_MOVE_1_SCORE
        if move == killer2:
            return  KILLER_MOVE_2_SCORE
        # 2. Ordered captures
        if target != ".":
            return CAPTURE_MOVE_VALUE + (10 * abs(piece_values[target]) - abs(piece_values[attacker]))

        return self.history_table[(sq_from << 6) | sq_to]

    def history_reduction_calc(self, sq_from, sq_to):
        reduction = 1
        history = self.history_table[sq_from << 6 | sq_to] # << 6 is equal to *64
        if history < 600:
            reduction = 2
        else:
            reduction = 1

        return reduction

    def update_history(self, sq_from, sq_to, depth):
        idx = (sq_from << 6) | sq_to
        self.history_table[idx] = min(self.history_table[idx] + (depth * depth) * 12, MAX_QUIET_MOVE_SCORE)
        