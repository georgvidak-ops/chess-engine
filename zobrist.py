import random

class Zobrist:
    def __init__(self):
        random.seed(23)
        pieces = "PNBRQKpnbrqk"

        self.piece_keys = {
            piece: [random.getrandbits(64) for _ in range(64)]
            for piece in pieces
        }
        self.side_key = random.getrandbits(64)
        
        self.castling_keys = [
            random.getrandbits(64)
            for _ in range(16)
        ]

        self.ep_keys = [
            random.getrandbits(64)
            for _ in range(8)
        ]

    def compute_hash(self, board):
        h = 0

        for sq in range(64):
            piece = board.get_piece(sq)

            if piece != ".":
                h ^= self.piece_keys[piece][sq]

        if board.white_to_move:
            h ^= self.side_key

        h ^= self.castling_keys[board.castling_rights]

        if board.en_passant_square:
            file = board.en_passant_square % 8
            h ^= self.ep_keys[file]

        return h