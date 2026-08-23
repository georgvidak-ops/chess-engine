from zobrist import Zobrist
from machine import Machine

MASK_64 = 0xFFFFFFFFFFFFFFFF

# file wrap masks
NOT_A_FILE  = 0xfefefefefefefefe
NOT_H_FILE  = 0x7f7f7f7f7f7f7f7f
NOT_AB_FILE = 0xfcfcfcfcfcfcfcfc
NOT_GH_FILE = 0x3f3f3f3f3f3f3f3f

# raycast arrays
ROOK_RAYS = [[0, 0, 0, 0] for _ in range(64)] # N, E, S, W
BISHOP_RAYS = [[0, 0, 0, 0] for _ in range(64)] # NW, NE, SE, SW
STRAIGHT = 0
DIAGONAL = 1

# eval shift types
MOVEMENT = 0
CAPTURE = 1
PROMOTION = 2
# en passant and castling are both variants of movement and capture types

# 64 x 64 array that returns True if 2 squares share a raycast (straight or diagonal)
SQUARES_ALIGNED = [[0] * 64 for _ in range(64)]
# 64 x 64 array that returns the bitboard of the ray between two squares if they share one
RAY_BETWEEN = [[0] * 64 for _ in range(64)]
# 64 x 64 array that returns the "infinite" ray that goes through two squares (if they fall on a ray)
RAY_LINE = [[0] * 64 for _ in range(64)]

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
        self.engine = Machine(self)
        self.eval_score = 0 # no need to initialize it in any way since starting position is considered equal
        
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
    # KNIGHT
    # -------------------------

    def KnightValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black

        r1, f1 = divmod(sq_from, 8)
        r2, f2 = divmod(sq_to, 8)

        if (abs(r1 - r2), abs(f1 - f2)) not in [(2,1),(1,2)]:
            return False

        return not ((1 << sq_to) & own)

    # -------------------------
    # BISHOP
    # -------------------------

    def bishop_moves(self, sq, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        return self.raycast_attacks(sq, DIAGONAL, enemy, raycasts)

    def BishopValidity(self, sq_from, sq_to, clr):
        enemy = self.black if clr else self.white

        moves = self.bishop_moves(sq_from, enemy, False)
        return bool(moves & (1 << sq_to))
    
    # -------------------------
    # ROOK
    # -------------------------
    def rook_moves(self, sq, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        return self.raycast_attacks(sq, STRAIGHT, enemy, raycasts)
    
    def RookValidity(self, sq_from, sq_to, clr):
        enemy = self.black if clr else self.white

        moves = self.rook_moves(sq_from, enemy, False)
        return bool(moves & (1 << sq_to))
    
    # -------------------------
    # QUEEN
    # -------------------------
    
    def queen_moves(self, sq, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        return self.rook_moves(sq, enemy, raycasts) | self.bishop_moves(sq, enemy, raycasts)

    def QueenValidity(self, sq_from, sq_to, clr):
        enemy = self.black if clr else self.white

        moves = self.queen_moves(sq_from, enemy, False)
        return bool(moves & (1 << sq_to))
    
    # -------------------------
    # KING
    # -------------------------

    def CheckCastling(self, type, clr): #type --> True = short castle, False = long castle
        if type and clr and (0b1000 & self.castling_rights):
            return not ((self.occupied & (1 << 61)) or (self.occupied & (1 << 62)))
        elif not type and clr and (0b0100 & self.castling_rights):
            return not ((self.occupied & (1 << 59)) or (self.occupied & (1 << 58)) or (self.occupied & (1 << 57)))
        if type and not clr and (0b0010 & self.castling_rights):
            return not ((self.occupied & (1 << 5)) or (self.occupied & (1 << 6)))
        elif not type and not clr and (0b0001 & self.castling_rights):
            return not ((self.occupied & (1 << 1)) or (self.occupied & (1 << 2)) or (self.occupied & (1 << 3)))

    def KingValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black

        r1, f1 = divmod(sq_from, 8)
        r2, f2 = divmod(sq_to, 8)


        if (abs(r1 - r2), abs(f1 - f2)) not in [(1,1),(1,0),(0,1)]:
            return False
        
        if ((1 << sq_to) & own): return False

        return True
    
    # -------------------------
    # ATTACK BITBOARDS
    # -------------------------

    def raycast_attacks(self, sq, dirs, enemy_bb, raycasts = False):
        rays = ROOK_RAYS[sq] if dirs == STRAIGHT else BISHOP_RAYS[sq]
        full_rays = ROOK_RAYS if dirs == STRAIGHT else BISHOP_RAYS

        occupied = self.occupied
        attacks = 0

        if dirs == STRAIGHT:
            rays = ROOK_RAYS[sq]
            msb_dirs = (True, False, False, True) # N, E, S, W
        else:
            rays = BISHOP_RAYS[sq]
            msb_dirs = (True, True, False, False) # NW, NE, SE, SW

        for i, ray in enumerate(rays):
            blockers = ray & occupied

            if not blockers:
                attacks |= ray
                continue

            if msb_dirs[i]:
                blocker = blockers.bit_length() - 1 # msb
            else:
                blocker = (blockers & -blockers).bit_length() - 1 # lsb

            blocker_bit = 1 << blocker

            # everything before the blocker, num represents the index of the opposite direction of ray
            num = (i+2) % 4
            attacks |= ray & full_rays[blocker][num]

            # can capture enemy blocker, but not own piece
            if (blocker_bit & enemy_bb) and not raycasts:
                attacks |= blocker_bit

        return attacks
        

    def pawn_attacks(self, from_sq, clr):
        pawns = self.wp if clr else self.bp
        if from_sq != None:
            pawns = 1 << from_sq

        attacks = 0

        if clr:
            attacks |= (pawns & NOT_A_FILE) >> 7
            attacks |= (pawns & NOT_H_FILE) >> 9
        else:   
            attacks |= (pawns & NOT_A_FILE) << 9
            attacks |= (pawns & NOT_H_FILE) << 7

        return attacks & MASK_64 #64 bit masking
    
    def knight_attacks(self, from_sq, clr):
        knights = self.wn if clr else self.bn
        if from_sq != None:
            knights = 1 << from_sq

        attacks = 0

        attacks |= (knights & NOT_H_FILE)  << 17
        attacks |= (knights & NOT_A_FILE)  << 15
        attacks |= (knights & NOT_GH_FILE) << 10
        attacks |= (knights & NOT_AB_FILE) << 6

        attacks |= (knights & NOT_H_FILE)  >> 15
        attacks |= (knights & NOT_A_FILE)  >> 17
        attacks |= (knights & NOT_GH_FILE) >> 6
        attacks |= (knights & NOT_AB_FILE) >> 10

        return attacks & MASK_64
    
    def rook_attacks(self, from_sq, clr):
        rooks = self.wr if clr else self.br
        if from_sq != None:
            rooks = 1 << from_sq

        enemy = self.black if clr else self.white
        squares = self.extract_squares(rooks)
        attacks = 0
        for i in squares:
            attacks |= self.rook_moves(i, enemy, True)
        return attacks

    def bishop_attacks(self, from_sq, clr):
        bishops = self.wb if clr else self.bb
        if from_sq != None:
            bishops = 1<< from_sq

        enemy = self.black if clr else self.white
        squares = self.extract_squares(bishops)
        attacks = 0
        for i in squares:
            attacks |= self.bishop_moves(i, enemy, True)
        return attacks
    
    def queen_attacks(self, from_sq, clr):
        queens = self.wq if clr else self.bq
        if from_sq != None:
            queens = 1 << from_sq

        enemy = self.black if clr else self.white
        squares = self.extract_squares(queens)
        attacks = 0
        for i in squares:
            attacks |= self.queen_moves(i, enemy, True)
        return attacks
    
    def king_attacker(self, clr):
        king = self.wk if clr else self.bk
        attacks = 0

        attacks |= (king & NOT_H_FILE)  << 1
        attacks |= (king & NOT_A_FILE)  << 7
        attacks |= king << 8
        attacks |= (king & NOT_H_FILE) << 9

        attacks |= (king & NOT_A_FILE)  >> 1
        attacks |= (king & NOT_H_FILE)  >> 7
        attacks |= king >> 8
        attacks |= (king & NOT_A_FILE) >> 9

        return attacks & MASK_64 #64 bit masking

    def pawn_attackers(self, sq, clr): #clr of the attacker
        target = 1 << sq

        if clr:
            # White pawns attack upwards, so reverse the attack.
            return ((target << 7) & NOT_H_FILE) | ((target << 9) & NOT_A_FILE)
        else:
            # Black pawns attack downwards.
            return ((target >> 7) & NOT_A_FILE) | ((target >> 9) & NOT_H_FILE)

    def knight_attackers(self, sq):
        if sq == -1:
            self.print_board()
        knight = 1 << sq

        attacks = 0

        attacks |= (knight & NOT_H_FILE)  << 17
        attacks |= (knight & NOT_A_FILE)  << 15
        attacks |= (knight & NOT_GH_FILE) << 10
        attacks |= (knight & NOT_AB_FILE) << 6

        attacks |= (knight & NOT_H_FILE)  >> 15
        attacks |= (knight & NOT_A_FILE)  >> 17
        attacks |= (knight & NOT_GH_FILE) >> 6
        attacks |= (knight & NOT_AB_FILE) >> 10

        return attacks & MASK_64

    def is_king_attacked(self, clr):
        enemy = self.black if clr else self.white
        own_king = self.wk if clr else self.bk
        knights = self.bn if clr else self.wn
        pawns = self.bp if clr else self.wp
        rooks = self.br if clr else self.wr
        queens = self.bq if clr else self.wq
        bishops = self.bb if clr else self.wb

        king_sq = own_king.bit_length() - 1

        if self.knight_attackers(king_sq) & knights:
            return True
        if self.king_attacker(clr) & own_king:
            return True
        if self.pawn_attackers(king_sq, not clr) & pawns:
            return True
        if self.rook_moves(king_sq, enemy, False) & (rooks | queens):
            return True
        if self.bishop_moves(king_sq, enemy, False) & (bishops | queens):
            return True
        return False

    def gives_check(self, clr, sq_from, sq_to):
        enemy = self.black if clr else self.white

        king_bit = self.bk if clr else self.wk
        king_sq = king_bit.bit_length() - 1

        piece = self.get_piece(sq_to)

        direct_attacks = 0

        if piece.upper() == 'P':
            direct_attacks = self.pawn_attackers(sq_to, clr)
        elif piece.upper() == 'N':
            direct_attacks = self.knight_attackers(sq_to)
        elif piece.upper() == 'B':
            direct_attacks = self.bishop_moves(sq_to, enemy, False)
        elif piece.upper() == 'R':
            direct_attacks = self.rook_moves(sq_to, enemy, False)
        elif piece.upper() == 'Q':
            direct_attacks = self.queen_moves(sq_to, enemy, False)
        elif piece.upper() == 'K':
            if abs(sq_from - sq_to) == 2: # in check after castle case
                if sq_to == 62: # white short castle
                    direct_attacks = 0x1F00000000000000
                elif sq_to == 58: # white long castle
                    direct_attacks = 0xF000000000000000
                elif sq_to == 6: # black short castle
                    direct_attacks = 0x000000000000001F
                elif sq_to == 2: # black long castle
                    direct_attacks = 0x00000000000000F0
                else:
                    direct_attacks = 0
        else:
            direct_attacks = 0

        if direct_attacks & king_bit:
            return True # direct hit

        if SQUARES_ALIGNED[sq_from][king_sq]: # discovered check possible
            return self.is_discovered_check(sq_from, sq_to, clr, piece)

        return False

    def is_discovered_check(self, sq_from, sq_to, clr, piece):
        enemy_king_sq = self.bk.bit_length() - 1 if clr else self.wk.bit_length() - 1

        if piece.upper() == "K":
            return self.is_king_attacked(not clr)
            
        # if sq_to stays on the same ray the moving piece still blocks the check
        if SQUARES_ALIGNED[sq_to][enemy_king_sq] and (RAY_LINE[sq_from][enemy_king_sq] == RAY_LINE[sq_to][enemy_king_sq]):
            return False

        # find own sliders behind sq_from along the king ray
        full_ray = RAY_LINE[sq_from][enemy_king_sq]
        
        own_sliders = (self.wq | self.wr | self.wb) if clr else (self.bq | self.br | self.bb)
        potential_attackers = own_sliders & full_ray
        
        if not potential_attackers:
            return False

        # verify sq_from was the only piece between a slider and the king
        for attacker_sq in self.extract_squares(potential_attackers):
            # make sure slider is behind sq_from relative to the king
            if (1 << sq_from) & RAY_BETWEEN[attacker_sq][enemy_king_sq]:
                # check if other piece blocks the path
                between_mask = RAY_BETWEEN[attacker_sq][enemy_king_sq] & ~(1 << sq_from)
                # handle en passant captured pawn removal from ray
                if piece.upper() == 'P' and sq_to == self.en_passant_square:
                    ep_pawn_sq = sq_to - 8 if clr else sq_to + 8
                    between_mask &= ~(1 << ep_pawn_sq)
                if (between_mask & self.occupied) == 0:
                    # check if piece type matches ray direction (Diagonal or Straight)
                    if self.valid_slider_for_ray(attacker_sq, enemy_king_sq):
                        return True

        return False

    def valid_slider_for_ray(self, sq, king_sq):
        if sq % 8 == king_sq % 8 or sq // 8 == king_sq // 8:
            # straight slider
            return (self.get_piece(sq).upper() in ("R", "Q"))
        else:
            # diagonal slider
            return (self.get_piece(sq).upper() in ("B", "Q"))

    
    # -------------------------
    # LEGAL MOVES
    # -------------------------
    def pawn_moves(self, from_sq, clr):
        occ = self.occupied
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
        attacks = self.pawn_attacks(from_sq, clr)

        enemy = self.black if clr else self.white

        moves |= attacks & enemy

        # en passant
        if self.en_passant_square is not None:
            ep_bit = 1 << self.en_passant_square

            if attacks & ep_bit:
                moves |= ep_bit

        return moves & MASK_64
    
    def pseudo_move_castling(self, clr):
        pseudo_castles = []
        rights = self.castling_rights
        king = self.wk if clr else self.bk

        from_sq = 60 if clr else 4
        to_sq_short = 62 if clr else 6
        to_sq_long  = 58 if clr else 2

        if rights == 0b0000 or king & (1 << from_sq):
            return pseudo_castles

        pieces_short = [61, 62] if clr else [5, 6]
        pieces_long  = [57, 58, 59] if clr else [1, 2, 3]

        can_s = all(not ((1 << sq) & self.occupied) for sq in pieces_short)
        can_l = all(not ((1 << sq) & self.occupied) for sq in pieces_long)

        mask_s = 0b1000 if clr else 0b0010
        mask_l = 0b0100 if clr else 0b0001

        enemy_attacks = (
            self.pawn_attacks(None, not clr)
            | self.knight_attacks(None, not clr)
            | self.bishop_attacks(None, not clr)
            | self.rook_attacks(None, not clr)
            | self.queen_attacks(None, not clr)
            | self.king_attacker(not clr)
        )

        if clr:
            safe_short = not (enemy_attacks & ((1 << 60) | (1 << 61) | (1 << 62)))
            safe_long  = not (enemy_attacks & ((1 << 60) | (1 << 59) | (1 << 58)))
        else:
            safe_short = not (enemy_attacks & ((1 << 4) | (1 << 5) | (1 << 6)))
            safe_long  = not (enemy_attacks & ((1 << 4) | (1 << 3) | (1 << 2)))

        if can_s and (self.castling_rights & mask_s) and safe_short:
            pseudo_castles.append((from_sq, to_sq_short))

        if can_l and (self.castling_rights & mask_l) and safe_long:
            pseudo_castles.append((from_sq, to_sq_long))

        return pseudo_castles
    
    def legal_move_castling(self, clr):
        pseudo_castles = self.pseudo_move_castling(clr)
        legal_castles = []

        for sq_from, sq_to in pseudo_castles:
            self.makeMove_sq(sq_from, sq_to, castleLegalityChecking=True)
            
            if not self.is_king_attacked(clr):
                legal_castles.append((sq_from, sq_to))

            self.unmakeMove_sq(sq_from, sq_to, castleLegalityChecking=True)

        return legal_castles

    
    def generate_pseudo_moves(self, clr):
        pseudo_moves = []
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

        for piece in pieces:
            bb = getattr(self, piece)

            while bb:
                from_bit = bb & -bb
                from_sq = from_bit.bit_length() - 1
                bb &= bb - 1  # remove LSB

                # generate pseudo-legal targets for this square
                if piece == "wp" or piece == "bp":
                    moves = self.pawn_moves(from_sq, clr)
                elif piece == "wn" or piece == "bn":
                    moves = self.knight_attacks(from_sq, clr) & ~own
                elif piece == "wb" or piece == "bb":
                    moves = self.bishop_moves(from_sq, enemy, False)
                elif piece == "wr" or piece == "br":
                    moves = self.rook_moves(from_sq, enemy, False)
                elif piece == "wq" or piece == "bq":
                    moves = self.queen_moves(from_sq, enemy, False)
                else:  # king
                    moves = self.king_attacker(clr) & ~own

                # iterate targets
                while moves:
                    to_bit = moves & -moves
                    to_sq = to_bit.bit_length() - 1
                    moves &= moves - 1

                    pseudo_moves.append((from_sq, to_sq))

        return pseudo_moves + self.pseudo_move_castling(clr)
    
    def generate_legal_moves(self, clr, in_check=False):
        legal_moves = []
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

        for piece in pieces:
            bb = getattr(self, piece)

            while bb:
                from_bit = bb & -bb
                from_sq = from_bit.bit_length() - 1
                bb &= bb - 1  # remove LSB

                # generate pseudo-legal targets for this square
                if piece[1] == "p":
                    moves = self.pawn_moves(from_sq, clr)
                elif piece[1] == "n":
                    moves = self.knight_attacks(from_sq, clr) & ~own
                elif piece[1] == "b":
                    moves = self.bishop_moves(from_sq, enemy, False)
                elif piece[1] == "r":
                    moves = self.rook_moves(from_sq, enemy, False)
                elif piece[1] == "q":
                    moves = self.queen_moves(from_sq, enemy, False)
                else:  # king
                    moves = self.king_attacker(clr) & ~own
                    

        # Had to repeat pseudo-legal generation because from_sq couldnt be passed as arguement without causing too much chaos


                # iterate targets
                while moves:
                    to_bit = moves & -moves
                    to_sq = to_bit.bit_length() - 1
                    moves &= moves - 1

                    # make move
                    self.makeMove_sq(from_sq, to_sq)

                    # legality check
                    if in_check:
                        if not self.is_king_attacked(clr):
                            legal_moves.append((from_sq, to_sq))
                    else:
                        piece_moved = self.get_piece(to_sq)
                        if not self.is_discovered_check(from_sq, to_sq, clr, piece_moved):
                            legal_moves.append((from_sq, to_sq))

                    # undo move
                    self.unmakeMove_sq(from_sq, to_sq)

        return legal_moves + self.legal_move_castling(clr)

    def generate_captures(self, clr):
        legal_captures = []
        enemy = self.black if clr else self.white
        captures = []

        pieces = ["wp","wn","wb","wr","wq","wk"] if clr else ["bp","bn","bb","br","bq","bk"]

        for piece in pieces:
            bb = getattr(self, piece)

            while bb:
                from_bit = bb & -bb
                from_sq = from_bit.bit_length() - 1
                bb &= bb - 1  # remove LSB

                # generate pseudo-legal targets for this square
                if piece[1] == "p":
                    captures = self.pawn_attackers(from_sq, clr) & enemy
                elif piece[1] == "n":
                    captures = self.knight_attacks(from_sq, clr) & enemy
                elif piece[1] == "b":
                    captures = self.bishop_moves(from_sq, enemy, False) & enemy
                elif piece[1] == "r":
                    captures = self.rook_moves(from_sq, enemy, False) & enemy
                elif piece[1] == "q":
                    captures = self.queen_moves(from_sq, enemy, False) & enemy
                else:  # king
                    captures = self.king_attacker(clr) & enemy    

                # iterate targets
                while captures:
                    to_bit = captures & -captures
                    to_sq = to_bit.bit_length() - 1
                    captures &= captures - 1

                    # make move
                    self.makeMove_sq(from_sq, to_sq)

                    # legality check
                    if not self.is_king_attacked(clr):
                        legal_captures.append((from_sq, to_sq))

                    # undo move
                    self.unmakeMove_sq(from_sq, to_sq)

        return legal_captures


    # -------------------------
    # PAWN
    # -------------------------

    def pawnValidity(self, sq_from, sq_to, clr):
        occ = self.occupied

        direction = -8 if clr else 8
        start_rank = 6 if clr else 1

        r1, f1 = divmod(sq_from, 8)
        f2 = sq_to % 8

        target = 1 << sq_to

        # forward move
        if f1 == f2:
            if sq_to == sq_from + direction and not (target & occ):
                return True

            if r1 == start_rank and sq_to == sq_from + 2 * direction:
                mid = sq_from + direction
                if not ((1 << mid) & occ) and not (target & occ):
                    #self.en_passant_square = mid
                    return True

        # capture
        if abs(f1 - f2) == 1 and abs(sq_to - sq_from) in (9, 7):
            enemy = self.black if clr else self.white
            if target & enemy:
                return True
            elif not (target & enemy) and self.en_passant_square  == sq_to:
                return True

        return False
    
    def promotion(self, sq, making): # making == True means the program is making a move, False means unmaking
        clr = self.white_to_move if making else not self.white_to_move
        queen_bb = self.wq if clr else self.bq
        pawn_bb = self.wp if clr else self.bp
        if making:
            pawn_bb &= ~(1 << sq) & MASK_64
            queen_bb |= (1 << sq)
        else:
            queen_bb &= ~(1 << sq) & MASK_64
            pawn_bb |= (1 << sq)

        attr1, attr2 = ("wp", "wq") if clr else ("bp", "bq")
        setattr(self, attr1, pawn_bb)
        setattr(self, attr2, queen_bb)

        return True


    # -------------------------
    # VALIDITY WRAPPER
    # -------------------------

    def checkValidity_sq(self, sq_from, sq_to):
        piece = self.get_piece(sq_from)
        if piece == ".":
            return False

        clr = piece.isupper()
        if clr != self.white_to_move:
            return False
        if piece.lower() == "p":
            return self.pawnValidity(sq_from, sq_to, clr)
        if piece.lower() == "n":
            return self.KnightValidity(sq_from, sq_to, clr)
        if piece.lower() == "b":
            return self.BishopValidity(sq_from, sq_to, clr)
        if piece.lower() == "r":
            return self.RookValidity(sq_from, sq_to, clr)
        if piece.lower() == "q":
            return self.QueenValidity(sq_from, sq_to, clr)
        if piece.lower() == "k":
            return self.KingValidity(sq_from, sq_to, clr)

        return False
    
    
    # -------------------------
    # CASTLE FUNCTION
    # -------------------------

    def castling_rights_modify(self, piece, sq_from):
        if piece == "K":
            self.castling_rights &= ~0b1100
        elif piece == "k":
            self.castling_rights &= ~0b0011

        elif piece == "R":
            if sq_from == 63:
                self.castling_rights &= ~0b1000
            elif sq_from == 56:
                self.castling_rights &= ~0b0100

        elif piece == "r":
            if sq_from == 7:
                self.castling_rights &= ~0b0010
            elif sq_from == 0:
                self.castling_rights &= ~0b0001

    def capture_castling_rights(self, sq):
        if sq == 63:
            self.castling_rights &= ~0b1000
        elif sq == 56:
            self.castling_rights &= ~0b0100
        elif sq == 7:
            self.castling_rights &= ~0b0010
        elif sq == 0:
            self.castling_rights &= ~0b0001

        

    def castle_rook_squares(self, sq_from, sq_to, clr):
        if sq_from == 60 and sq_to == 62 and clr:      # White O-O
            return 63, 61
        elif sq_from == 60 and sq_to == 58 and clr:    # White O-O-O
            return 56, 59
        elif sq_from == 4 and sq_to == 6 and not clr:      # Black O-O
            return 7, 5
        elif sq_from == 4 and sq_to == 2 and not clr:      # Black O-O-O
            return 0, 3

        return None

    def castle(self, sq_from, sq_to, making, clr):
        r = self.castle_rook_squares(sq_from, sq_to, clr)

        from_sq, to_sq = (0,0)
        if making:
            from_sq, to_sq = r
        else:
            to_sq, from_sq = r

        return from_sq, to_sq


    # -------------------------
    # MAKE MOVE
    # -------------------------

    def makeMove_sq(self, sq_from, sq_to, castleLegalityChecking=False):
        piece = self.get_piece(sq_from)
        mapping = {
            "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
            "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
        }
        old_en_passant_square = 0
        old_eval = self.eval_score

        if piece == ".":
            return False

        # castling
        if abs(sq_to - sq_from) == 2 and piece.lower() == "k" and not castleLegalityChecking:
            r_piece = "r" if piece == "k" else "R"
            # setting variables
            sq_from_rook, sq_to_rook = self.castle(sq_from, sq_to, True, self.white_to_move)
            to_bit = 1 << sq_to_rook
            from_bit = 1 << sq_from_rook
            # moving rook
            bb = getattr(self, mapping[r_piece])
            bb &= ~from_bit & MASK_64
            bb |= to_bit
            setattr(self, mapping[r_piece], bb)
            # shift eval
            self.eval_score += self.engine.shift_eval(
                self.white_to_move, # clr
                MOVEMENT, # type
                move = (sq_from_rook, sq_to_rook), # move
                piece = r_piece
            )

            self.hash ^= self.zobrist.piece_keys[r_piece][sq_from_rook]
            self.hash ^= self.zobrist.piece_keys[r_piece][sq_to_rook]
        
        # remove old EP from hash
        if self.en_passant_square:
            self.hash ^= self.zobrist.ep_keys[self.en_passant_square % 8]

        old_en_passant_square = self.en_passant_square

        # update EP state
        if piece.lower() == "p" and abs(sq_to - sq_from) == 16:
            self.en_passant_square = (sq_from + sq_to) // 2
        else:
            self.en_passant_square = 0

        # add new EP to hash
        if self.en_passant_square:
            self.hash ^= self.zobrist.ep_keys[self.en_passant_square % 8]

        # handle EP
        was_en_passant = False
        if not ((1 << sq_to) & self.occupied) and piece.upper() == "P" and abs(sq_to - sq_from) in (7, 9) and sq_to == old_en_passant_square:
            #if these conditions are met then the move was a pawn that captured another via en passant
            was_en_passant = True

            #shift eval
            self.eval_score += self.engine.shift_eval(
                self.white_to_move, # clr
                CAPTURE, # type
                piece = "P"
            )

            self.en_passant_capture_removal(sq_to, self.white_to_move)

        # remove old castling rights
        self.hash ^= self.zobrist.castling_keys[self.castling_rights]
        
        old_castling_rights = self.castling_rights
        self.castling_rights_modify(piece, sq_from)

        from_bit = 1 << sq_from
        to_bit = 1 << sq_to

        self.just_promoted = False

        captured_piece = "."
        if was_en_passant:
            captured_piece = "bp" if self.white_to_move else "wp"
            direction = 8 if self.white_to_move else - 8
            self.hash ^= self.zobrist.piece_keys[self.translate(captured_piece)][sq_to + direction]
        # capture removal
        for attr in [self.wp, self.wn, self.wb, self.wr, self.wq, self.wk, self.bp, self.bn, self.bb, self.br, self.bq, self.bk]:
            if attr & to_bit:
                captured_piece = self.translate(attr)

                if captured_piece == "wr" or captured_piece == "br":
                    self.capture_castling_rights(sq_to)

                self.hash ^= self.zobrist.piece_keys[self.translate(captured_piece)][sq_to]
                setattr(self, captured_piece, getattr(self, captured_piece) & ~to_bit)

                # shift eval
                self.eval_score += self.engine.shift_eval(
                    self.white_to_move, # clr
                    CAPTURE, # type
                    piece = self.translate(captured_piece) # captured piece is passed as an argument instead of moved piece when move is a capture
                )


        # add new castling rights to hash
        self.hash ^= self.zobrist.castling_keys[self.castling_rights]
        
        # move piece

        self.hash ^= self.zobrist.piece_keys[piece][sq_from]
        self.hash ^= self.zobrist.piece_keys[piece][sq_to]

        bb = getattr(self, mapping[piece])
        bb &= ~from_bit & MASK_64
        bb |= to_bit
        setattr(self, mapping[piece], bb)

        # shift eval
        self.eval_score += self.engine.shift_eval(
            self.white_to_move, # clr
            MOVEMENT, # type
            move = (sq_from, sq_to), # move
            piece = piece
        )

        # promotion
        if piece.lower() == "p" and sq_to // 8 in (0,7):
            self.just_promoted = True
            self.promotion(sq_to, True)
            self.hash ^= self.zobrist.piece_keys[piece][sq_to]
            queen = "Q" if piece == "P" else "q"
            self.hash ^= self.zobrist.piece_keys[queen][sq_to]

            # shift eval
            self.eval_score += self.engine.shift_eval(
                self.white_to_move, # clr
                PROMOTION, # type
                piece = "P"
            )

        self.white_to_move = not self.white_to_move

        # move stacking in memory
        moved_piece = piece
        promotion_happened = self.just_promoted
        old_white_to_move_after = self.white_to_move

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
        self.hash ^= self.zobrist.side_key # update side-to-move hash key
        self.move_stack.append(move_state)

        self.white = self.wp | self.wn | self.wb | self.wr | self.wq | self.wk
        self.black = self.bp | self.bn | self.bb | self.br | self.bq | self.bk
        self.occupied = self.white | self.black

        return True
    
    def unmakeMove_sq(self, sq_from, sq_to, castleLegalityChecking=False): # sq_from and #sq_to refer to the original move's sq_from and sq_to
        moved_piece, old_en_passant_square, old_castling_rights, promotion_happened, old_white_to_move_after, old_eval = (0,0,0,0,0,0)
        captured_piece = "."
        was_en_passant = False
        mapping = {
            "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
            "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
        }
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
        ) = self.move_stack.pop()

        # restoring eval
        self.eval_score = old_eval

        # restoring castle
        if abs(sq_to - sq_from) == 2 and moved_piece.lower() == "k" and not castleLegalityChecking:
            r_piece = "r" if moved_piece == "k" else "R"
            # setting variables
            sq_from_rook, sq_to_rook = self.castle(sq_from, sq_to, False, not self.white_to_move) # color inversed because during unmake_move, make_move has already given turn to other player
            to_bit = 1 << sq_to_rook
            from_bit = 1 << sq_from_rook
            # moving rook
            bb = getattr(self, mapping[r_piece])
            bb &= ~from_bit & MASK_64
            bb |= to_bit
            setattr(self, mapping[r_piece], bb)

            self.hash ^= self.zobrist.piece_keys[r_piece][sq_from_rook]
            self.hash ^= self.zobrist.piece_keys[r_piece][sq_to_rook]


        from_bit = 1 << sq_from
        to_bit = 1 << sq_to

        self.hash ^= self.zobrist.side_key

        self.hash ^= self.zobrist.piece_keys[moved_piece][sq_from]
        self.hash ^= self.zobrist.piece_keys[moved_piece][sq_to]
        if captured_piece != ".":
            if was_en_passant:
                direction = -8 if self.white_to_move else +8
                self.hash ^= self.zobrist.piece_keys[self.translate(captured_piece)][sq_to + direction]
            else:
                self.hash ^= self.zobrist.piece_keys[self.translate(captured_piece)][sq_to]
        
        self.hash ^= self.zobrist.castling_keys[self.castling_rights] # remove hashed rights of move
        self.hash ^= self.zobrist.castling_keys[old_castling_rights] # hash rights before move

        if self.en_passant_square:
            self.hash ^= self.zobrist.ep_keys[self.en_passant_square % 8] # remove hashed ep square of move
        if old_en_passant_square:
            self.hash ^= self.zobrist.ep_keys[old_en_passant_square % 8] # hash ep square before move
        

        # undo promotion
        if moved_piece.lower() == "p" and sq_to // 8 in (0,7) and promotion_happened:
            queen = "Q" if moved_piece == "P" else "q"
            self.hash ^= self.zobrist.piece_keys[queen][sq_to]
            self.hash ^= self.zobrist.piece_keys[moved_piece][sq_to]
            self.promotion(sq_to, False)

        # move piece back
        bb = getattr(self, mapping[moved_piece])
        bb &= ~to_bit & MASK_64
        bb |= from_bit
        setattr(self, mapping[moved_piece], bb)

        # restore captured piece
        if captured_piece != ".":
            if was_en_passant:
                self.en_passant_capture_restoration(sq_to, not self.white_to_move) # color inversed because during unmake_move, make_move has already given turn to other player
            else:
                cap_bb = getattr(self, captured_piece)

                cap_bb |= to_bit

                setattr(self, captured_piece, cap_bb)

        self.en_passant_square = old_en_passant_square

        self.castling_rights = old_castling_rights

        self.white_to_move = not old_white_to_move_after

        self.white = self.wp | self.wn | self.wb | self.wr | self.wq | self.wk
        self.black = self.bp | self.bn | self.bb | self.br | self.bq | self.bk
        self.occupied = self.white | self.black

        return True

    def make_null_move(self):
        self.white_to_move = not self.white_to_move
        self.hash ^= self.zobrist.side_key

        if self.en_passant_square:
            self.hash ^= self.zobrist.ep_keys[self.en_passant_square % 8]
            ep = self.en_passant_square
            self.en_passant_square = 0
            return ep
        return False

    def unmake_null_move(self, ep_sq):
        self.hash ^= self.zobrist.side_key
        self.white_to_move = not self.white_to_move

        if ep_sq:
            self.hash ^= self.zobrist.ep_keys[ep_sq % 8]
            self.en_passant_square = ep_sq

    def en_passant_capture_removal(self, sq_to, clr):
        direction = 8 if clr else -8

        to_bit = 1 << (sq_to + direction)
        attr = "bp" if clr else "wp"
        if getattr(self, attr) & to_bit:
            setattr(self, attr, getattr(self, attr) & ~to_bit & MASK_64)

        return

    def en_passant_capture_restoration(self, sq_to, clr):
        direction = 8 if clr else -8
        
        to_bit = 1 << (sq_to + direction)

        attr = "bp" if clr else "wp"
        setattr(self, attr, getattr(self, attr) | to_bit & MASK_64)

        return
                
    
    # -------------------------
    # PERFT TESTING
    # -------------------------

    def perft(self, depth, clr, root_depth=None):
        # If root_depth isn't set, initialize it to the starting depth
        if root_depth is None:
            root_depth = depth

        # reached leaf node
        if depth == 0:
            return 1

        nodes = 0

        # generate all legal moves
        legal_moves = self.generate_legal_moves(clr)

        # recurse through move tree
        for sq_from, sq_to in legal_moves:

            # make move
            self.makeMove_sq(sq_from, sq_to)
            # recurse and get count for this specific branch
            branch_nodes = self.perft(depth - 1, not clr, root_depth)
            nodes += branch_nodes

            # undo move
            self.unmakeMove_sq(sq_from, sq_to)

            # SPLIT/DIVIDE: If at the top-most level of the search, print the results for this move
            if depth == root_depth:
                move_str = f"{sq_from} -> {sq_to}" 
                print(f"{move_str}: {branch_nodes}")

        # Print summary line
        if depth == root_depth:
            print(f"\nTotal Nodes: {nodes}")

        return nodes


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