from zobrist import Zobrist
from machine import Machine

MASK_64 = 0xFFFFFFFFFFFFFFFF

# eval shift types
MOVEMENT = 0
CAPTURE = 1
PROMOTION = 2
# en passant and castling are both variants of movement and capture types

class Board:
    def __init__(self):
        self.init_bitboards()
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

    # -------------------------
    # BITBOARDS
    # -------------------------

    @property
    def white(self):
        return self.wp | self.wn | self.wb | self.wr | self.wq | self.wk

    @property
    def black(self):
        return self.bp | self.bn | self.bb | self.br | self.bq | self.bk

    @property
    def occupied(self):
        return self.white | self.black

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

        lets = ["p", "n", "b", "r", "q", "k", "P", "N", "B", "R", "Q", "K"]
        idxs = ["bp", "bn", "bb", "br", "bq", "bk", "wp", "wn", "wb", "wr", "wq", "wk"]

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

    def bishop_moves(self, sq, own, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        moves = 0
        occupied = self.occupied
        for d in [9, 7, -7, -9]:
            s = sq

            while True:
                prev = s
                s += d

                if s < 0 or s > 63:
                    break

                # file wrap check
                if abs((s % 8) - (prev % 8)) != 1:
                    break

                bit = 1 << s

                if raycasts:
                    moves |= bit
                    if bit & occupied:
                        break
                else:
                    if bit & own:
                        break
                    moves |= bit
                    if bit & enemy:
                        break

        return moves

    def BishopValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.bishop_moves(sq_from, own, enemy, False)
        return bool(moves & (1 << sq_to))
    
    # -------------------------
    # ROOK
    # -------------------------
    def rook_moves(self, sq, own, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        moves = 0
        occupied = self.occupied
        #veritcal check
        for d in [8, -8]:
            s = sq

            while True:
                prev = s
                s += d

                if s < 0 or s > 63:
                    break

                bit = 1 << s

                if raycasts:
                    moves |= bit
                    if bit & occupied:
                        break
                else:
                    if bit & own:
                        break
                    moves |= bit
                    if bit & enemy:
                        break
        
        #horizontal check (requires file wrapping protection)
        for d in [1, -1]:
            s = sq

            while True:
                prev = s
                s += d

                if s < 0 or s > 63:
                    break

                if (s//8) != (prev//8): break

                bit = 1 << s

                if raycasts:
                    moves |= bit
                    if bit & occupied:
                        break
                else:
                    if bit & own:
                        break
                    moves |= bit
                    if bit & enemy:
                        break

        return moves
    
    def RookValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.rook_moves(sq_from, own, enemy, False)

        if not bool(moves & (1 << sq_to)): return False

        return True
    
    # -------------------------
    # QUEEN
    # -------------------------
    
    def queen_moves(self, sq, own, enemy, raycasts): # raycasts = True tells the programme to not count any object it hit whether its own or enemy piece
        return self.rook_moves(sq, own, enemy, raycasts) | self.bishop_moves(sq, own, enemy, raycasts)

    def QueenValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.queen_moves(sq_from, own, enemy, False)
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
    def pawn_attacks(self, from_sq, clr):
        pawns = self.wp if clr else self.bp
        if from_sq != None:
            pawns = 1 << from_sq

        NOT_H_FILE = 0xfefefefefefefefe
        NOT_A_FILE = 0x7f7f7f7f7f7f7f7f

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

        NOT_A_FILE  = 0xfefefefefefefefe
        NOT_H_FILE  = 0x7f7f7f7f7f7f7f7f
        NOT_AB_FILE = 0xfcfcfcfcfcfcfcfc
        NOT_GH_FILE = 0x3f3f3f3f3f3f3f3f

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

        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(rooks)
        attacks = 0
        for i in squares:
            attacks |= self.rook_moves(i, own, enemy, True)
        return attacks

    def bishop_attacks(self, from_sq, clr):
        bishops = self.wb if clr else self.bb
        if from_sq != None:
            bishops = 1<< from_sq

        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(bishops)
        attacks = 0
        for i in squares:
            attacks |= self.bishop_moves(i, own, enemy, True)
        return attacks
    
    def queen_attacks(self, from_sq, clr):
        queens = self.wq if clr else self.bq
        if from_sq != None:
            queens = 1 << from_sq

        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(queens)
        attacks = 0
        for i in squares:
            attacks |= self.queen_moves(i, own, enemy, True)
        return attacks
    
    def king_attacker(self, clr):
        king = self.wk if clr else self.bk
        NOT_A_FILE  = 0xfefefefefefefefe
        NOT_H_FILE  = 0x7f7f7f7f7f7f7f7f
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

        NOT_A_FILE = 0x7f7f7f7f7f7f7f7f
        NOT_H_FILE = 0xfefefefefefefefe

        if clr:
            # White pawns attack upwards, so reverse the attack.
            return ((target << 7) & NOT_H_FILE) | ((target << 9) & NOT_A_FILE)
        else:
            # Black pawns attack downwards.
            return ((target >> 7) & NOT_A_FILE) | ((target >> 9) & NOT_H_FILE)

    def knight_attackers(self, sq):
        knight = 1 << sq

        NOT_A_FILE  = 0xfefefefefefefefe
        NOT_H_FILE  = 0x7f7f7f7f7f7f7f7f
        NOT_AB_FILE = 0xfcfcfcfcfcfcfcfc
        NOT_GH_FILE = 0x3f3f3f3f3f3f3f3f

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
        own = self.white if clr else self.black
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
        if self.rook_moves(king_sq, own, enemy, False) & (rooks | queens):
            return True
        if self.bishop_moves(king_sq, own, enemy, False) & (bishops | queens):
            return True
        return False
    
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
                    moves = self.bishop_moves(from_sq, own, enemy, False)
                elif piece == "wr" or piece == "br":
                    moves = self.rook_moves(from_sq, own, enemy, False)
                elif piece == "wq" or piece == "bq":
                    moves = self.queen_moves(from_sq, own, enemy, False)
                else:  # king
                    moves = self.king_attacker(clr) & ~own

                # iterate targets
                while moves:
                    to_bit = moves & -moves
                    to_sq = to_bit.bit_length() - 1
                    moves &= moves - 1

                    pseudo_moves.append((from_sq, to_sq))

        return pseudo_moves + self.pseudo_move_castling(clr)
    
    def generate_legal_moves(self, clr, capturesOnly = False):
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
                    moves = self.bishop_moves(from_sq, own, enemy, False)
                elif piece[1] == "r":
                    moves = self.rook_moves(from_sq, own, enemy, False)
                elif piece[1] == "q":
                    moves = self.queen_moves(from_sq, own, enemy, False)
                else:  # king
                    moves = self.king_attacker(clr) & ~own
                    

        # Had to repeat pseudo-legal generation because from_sq couldnt be passed as arguement without causing too much chaos


                # iterate targets
                while moves:
                    to_bit = moves & -moves
                    to_sq = to_bit.bit_length() - 1
                    moves &= moves - 1

                    is_quiet = not (to_bit & enemy)
                    is_ep = False
                    if piece == "wp" or "bp" and to_sq == self.en_passant_square:
                        is_ep == True

                    if (is_quiet or is_ep) and capturesOnly:
                        continue

                    # make move
                    self.makeMove_sq(from_sq, to_sq)

                    # legality check
                    if not self.is_king_attacked(clr):
                        legal_moves.append((from_sq, to_sq))

                    # undo move
                    self.unmakeMove_sq(from_sq, to_sq)

        if capturesOnly: return legal_moves
        return legal_moves + self.legal_move_castling(clr)


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
        if self.get_piece(sq_to) == "." and piece.upper() == "P" and abs(sq_to - sq_from) in (7, 9) and sq_to == old_en_passant_square:
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
        for attr in ["wp","wn","wb","wr","wq","wk","bp","bn","bb","br","bq","bk"]:
            if getattr(self, attr) & to_bit:
                captured_piece = attr

                if captured_piece == "wr" or captured_piece == "br":
                    self.capture_castling_rights(sq_to)

                self.hash ^= self.zobrist.piece_keys[self.translate(captured_piece)][sq_to]
                setattr(self, attr, getattr(self, attr) & ~to_bit)

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
                direction = 8 if self.white_to_move else -8
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

        return True

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