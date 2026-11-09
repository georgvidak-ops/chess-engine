from zobrist import Zobrist

from .constants import (
    ROOK_RAYS,
    BISHOP_RAYS,
    SQUARES_ALIGNED,
    RAY_BETWEEN,
    RAY_LINE
)

class Board:
    def __init__(self):
        self.init_bitboards()
        self.init_rays()
        self.init_alignment_table()
        self.init_between_rays()
        self.init_ray_line()
        self.white_to_move = True
        self.castling_rights = 0b1111 #each bit represents a castling right 1)White short, 2)White long, 3)Black short, 4)Black long
        self.en_passant_square = 0
        self.captured_piece = "."
        self.just_promoted = False
        self.move_stack = []
        self.eval_score = 0 # no need to initialize it in any way since starting position is considered equal
        self.principal_variation = []
        
        self.zobrist = Zobrist()
        self.hash = self.zobrist.compute_hash(self)

        

    # -------------------------
    # INIT POSITION
    # -------------------------

    def init_bitboards(self):
        # pawns
        self.wp = 0x00FF000000000000
        self.bp = 0x000000000000FF00

        # pieces
        self.br = (1<<0) | (1<<7)
        self.bn = (1<<1) | (1<<6)
        self.bb = (1<<2) | (1<<5)
        self.bq = (1<<3)
        self.bk = (1<<4)

        self.wr = (1<<56) | (1<<63)
        self.wn = (1<<57) | (1<<62)
        self.wb = (1<<58) | (1<<61)
        self.wq = (1<<59)
        self.wk = (1<<60)

        self.white = self.wp | self.wn | self.wb | self.wr | self.wq | self.wk
        self.black = self.bp | self.bn | self.bb | self.br | self.bq | self.bk
        self.occupied = self.white | self.black

    def init_rays(self):
        for sq in range(64):
            rank = sq // 8
            file = sq % 8

            # Rook: N, E, S, W
            if rank > 0:
                for r in range(rank - 1, -1, -1):
                    ROOK_RAYS[sq][0] |= 1 << (r * 8 + file)

            if file < 7:
                for f in range(file + 1, 8):
                    ROOK_RAYS[sq][1] |= 1 << (rank * 8 + f)

            if rank < 7:
                for r in range(rank + 1, 8):
                    ROOK_RAYS[sq][2] |= 1 << (r * 8 + file)

            if file > 0:
                for f in range(file - 1, -1, -1):
                    ROOK_RAYS[sq][3] |= 1 << (rank * 8 + f)

            # Bishop: NW, NE, SE, SW
            r, f = rank - 1, file - 1
            while r >= 0 and f >= 0:
                BISHOP_RAYS[sq][0] |= 1 << (r * 8 + f)
                r -= 1
                f -= 1

            r, f = rank - 1, file + 1
            while r >= 0 and f < 8:
                BISHOP_RAYS[sq][1] |= 1 << (r * 8 + f)
                r -= 1
                f += 1

            r, f = rank + 1, file + 1
            while r < 8 and f < 8:
                BISHOP_RAYS[sq][2] |= 1 << (r * 8 + f)
                r += 1
                f += 1

            r, f = rank + 1, file - 1
            while r < 8 and f >= 0:
                BISHOP_RAYS[sq][3] |= 1 << (r * 8 + f)
                r += 1
                f -= 1

    def init_alignment_table(self): # first 64 
        for f in range(64): # f = sq_from
            for t in range(64): # t = sq_to
                if f // 8 == t // 8: # same rank
                    SQUARES_ALIGNED[f][t] = True
                elif f % 8 == t % 8: # same file
                    SQUARES_ALIGNED[f][t] = True 
                elif abs(f % 8 - t % 8) == abs(f // 8 - t // 8): # share a diagonal
                    SQUARES_ALIGNED[f][t] = True
                elif f == t: # same square
                    SQUARES_ALIGNED[f][t] = True
                else:
                    SQUARES_ALIGNED[f][t] = False

    def init_between_rays(self):
        for f in range(64): # f = sq_from
            for t in range(64): # t = sq_to
                if SQUARES_ALIGNED[f][t]:
                    # Walk square-by-square from sq_from toward sq_to
                    step_r = (t // 8 - f // 8) # step rank
                    step_r = 0 if step_r == 0 else (1 if step_r > 0 else -1)
                    
                    step_f = (t % 8 - f % 8) # step file
                    step_f = 0 if step_f == 0 else (1 if step_f > 0 else -1)
                    
                    curr_r, curr_f = f // 8 + step_r, f % 8 + step_f
                    mask = 0
                    
                    while (curr_r, curr_f) != (t // 8, t % 8):
                        mask |= (1 << (curr_r * 8 + curr_f))
                        curr_r += step_r
                        curr_f += step_f
                        
                    RAY_BETWEEN[f][t] = mask
                else:
                    continue

    def init_ray_line(self):
        for sq_from in range(64):
            f_rank, f_file = sq_from // 8, sq_from % 8
            
            for sq_to in range(64):
                if sq_from == sq_to:
                    continue
                    
                t_rank, t_file = sq_to // 8, sq_to % 8
                
                # step direction (-1, 0, or 1) for rank and file
                step_r = t_rank - f_rank
                step_r = 0 if step_r == 0 else (1 if step_r > 0 else -1)
                
                step_f = t_file - f_file
                step_f = 0 if step_f == 0 else (1 if step_f > 0 else -1)
                
                # only generate lines if squares are aligned
                if not SQUARES_ALIGNED[sq_from][sq_to]:
                    continue
                
                line_mask = 0
                
                # walk all the way in the forward direction to the edge of the board
                r, f = f_rank, f_file
                while 0 <= r < 8 and 0 <= f < 8:
                    line_mask |= (1 << (r * 8 + f))
                    r += step_r
                    f += step_f
                    
                # walk all the way in the backward direction to the opposite edge
                r, f = f_rank - step_r, f_file - step_f
                while 0 <= r < 8 and 0 <= f < 8:
                    line_mask |= (1 << (r * 8 + f))
                    r -= step_r
                    f -= step_f
                    
                RAY_LINE[sq_from][sq_to] = line_mask
                

    # -------------------------
    # SQUARE HELPERS
    # -------------------------

    def get_piece(self, sq):
        bit = 1 << sq

        if self.wp & bit: return "P"
        if self.wn & bit: return "N"
        if self.wb & bit: return "B"
        if self.wr & bit: return "R"
        if self.wq & bit: return "Q"
        if self.wk & bit: return "K"

        if self.bp & bit: return "p"
        if self.bn & bit: return "n"
        if self.bb & bit: return "b"
        if self.br & bit: return "r"
        if self.bq & bit: return "q"
        if self.bk & bit: return "k"

        return "."
        
    def extract_squares(self, bb):
        squares = []

        while bb:
            lsb = bb & -bb
            sq = lsb.bit_length() - 1
            squares.append(sq)
            bb &= bb - 1

        return squares

    # -------------------------
    # MOVE CONVERSION
    # -------------------------

    def parse(self, move):
        f_file, f_rank, t_file, t_rank = move

        from_sq = (8 - int(f_rank)) * 8 + (ord(f_file) - ord('a'))
        to_sq   = (8 - int(t_rank)) * 8 + (ord(t_file) - ord('a'))

        return from_sq, to_sq

    def reverse_parse(self, from_sq, to_sq):
        f_rank, f_file = divmod(from_sq, 8)
        t_rank, t_file = divmod(to_sq, 8)

        return f"{chr(f_file + ord('a'))}{8 - f_rank}{chr(t_file + ord('a'))}{8 - t_rank}"

    def translate(self, str):
        if str == ".": return str

        bbs = [self.bp, self.bn, self.bb, self.br, self.bq, self.bk, self.wp, self.wn, self.wb, self.wr, self.wq, self.wk]
        lets = ["p", "n", "b", "r", "q", "k", "P", "N", "B", "R", "Q", "K"]
        idxs = ["bp", "bn", "bb", "br", "bq", "bk", "wp", "wn", "wb", "wr", "wq", "wk"]

        if str in bbs:
            return idxs[bbs.index(str)]
        if str in idxs:
            return lets[idxs.index(str)]
        if str in lets:
            return idxs[lets.index(str)]


    # -------------------------
    # PRINT BOARD
    # -------------------------

    def print_board(self):
        for r in range(8):
            row = []
            for f in range(8):
                sq = r * 8 + f
                row.append(self.get_piece(sq))
            print(" ".join(row))
        print()