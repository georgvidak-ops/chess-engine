class Board:
    def __init__(self):
        self.init_bitboards()
        self.white_to_move = True
        self.castling_rights = 0b1111 #each bit represents a castling right 1)White short, 2)White long, 3)Black short, 4)Black long
        self.en_passant_square = 0

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

        pieces = {
            "P": self.wp, "N": self.wn, "B": self.wb,
            "R": self.wr, "Q": self.wq, "K": self.wk,
            "p": self.bp, "n": self.bn, "b": self.bb,
            "r": self.br, "q": self.bq, "k": self.bk,
        }

        for p, bb in pieces.items():
            if bb & bit:
                return p
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

    def bishop_moves(self, sq, own, enemy, raycasts):
        moves = 0
        occupied = own | enemy
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
    def rook_moves(self, sq, own, enemy, raycasts):
        moves = 0
        occupied = own | enemy
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

        if not bool(moves & (1 << sq_to)): return False #no need to check for castling rights if move is invalid
        if clr and (self.castling_rights & 0b1000) and sq_from & (1 << 63): #check if white's a1 rook moved and removed castling rights
            self.castling_rights ^= 0b1000
        elif clr and (self.castling_rights & 0b0100) and sq_from & (1 << 56): #check if white's h1 rook moved and removed castling rights
            self.castling_rights ^= 0b0100
        elif not clr and (self.castling_rights & 0b0010) and sq_from & (1 << 0): #check if black's a8 rook moved and removed castling rights
            self.castling_rights ^= 0b0010
        elif not clr and (self.castling_rights & 0b0001) and sq_from & (1 << 7): #check if black's h8 rook moved and removed castling rights
            self.castling_rights ^= 0b0001

        return True
    
    # -------------------------
    # QUEEN
    # -------------------------
    
    def queen_moves(self, sq, own, enemy, raycasts):
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

        self.castling_rights &= ~0b1100 if clr else ~0b0011

        return True
    
    # -------------------------
    # ATTACK BITBOARDS
    # -------------------------
    def pawn_attacks(self, clr):
        pawns = self.wp if clr else self.bp

        NOT_A_FILE = 0xfefefefefefefefe
        NOT_H_FILE = 0x7f7f7f7f7f7f7f7f

        attacks = 0

        if clr:
            attacks  |= (pawns & NOT_A_FILE) >> 7
            attacks |= (pawns & NOT_H_FILE) >> 9
        else:   
            attacks |= (pawns & NOT_A_FILE) << 9
            attacks |= (pawns & NOT_H_FILE) << 7

        return attacks & 0xFFFFFFFFFFFFFFFF #64 bit masking
    
    def knight_attacks(self, clr):
        knights = self.wn if clr else self.bn

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

        return attacks & 0xFFFFFFFFFFFFFFFF
    
    def rook_attacks(self, clr):
        rooks = self.wr if clr else self.br
        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(rooks)
        attacks = 0
        for i in squares:
            attacks |= self.rook_moves(i, own, enemy, True)
        return attacks

    def bishop_attacks(self, clr):
        bishops = self.wb if clr else self.bb
        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(bishops)
        attacks = 0
        for i in squares:
            attacks |= self.bishop_moves(i, own, enemy, True)
        return attacks
    
    def queen_attacks(self, clr):
        queens = self.wq if clr else self.bq
        own, enemy = (self.white, self.black) if clr else (self.black, self.white)
        squares = self.extract_squares(queens)
        attacks = 0
        for i in squares:
            attacks |= self.queen_moves(i, own, enemy, True)
        return attacks
    
    def king_attacks(self, clr):
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

        return attacks & 0xFFFFFFFFFFFFFFFF #64 bit masking


    def king_in_check(self, clr):
        enemy_attack_board = self.pawn_attacks(not clr) | self.knight_attacks(not clr) | self.bishop_attacks(not clr) | self.rook_attacks(not clr) | self.queen_attacks(not clr) | self.king_attacks(not clr)
        king = self.wk if clr else self.bk
        if king & enemy_attack_board:
            return True
        return False


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
                    self.en_passant_square = mid
                    return True

        # capture
        if abs(f1 - f2) == 1 and abs(sq_to - sq_from) in (9, 7):
            enemy = self.black if clr else self.white
            if target & enemy:
                return True
            elif not (target & enemy) and self.en_passant_square  == sq_to:
                self.en_passant_capture_removal(sq_to - direction)
                return True

        return False

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
    # MAKE MOVE
    # -------------------------

    def makeMove_sq(self, sq_from, sq_to, castling):
        piece = self.get_piece(sq_from)
        if piece == ".":
            return False

        from_bit = 1 << sq_from
        to_bit = 1 << sq_to

        # en_passant_sqaure reset
        if not (abs(sq_from - sq_to) == 16 and piece.lower() == "p"): # double pawn push
            self.en_passant_square = 0

        # capture removal
        for attr in ["wp","wn","wb","wr","wq","wk","bp","bn","bb","br","bq","bk"]:
            if getattr(self, attr) & to_bit:
                setattr(self, attr, getattr(self, attr) & ~to_bit)

        # move piece
        mapping = {
            "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
            "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
        }

        bb = getattr(self, mapping[piece])
        bb &= ~from_bit
        bb |= to_bit
        setattr(self, mapping[piece], bb)

        self.white_to_move = not self.white_to_move if not castling else self.white_to_move
        return True
    
    def unmakeMove_sq(self, sq_from, sq_to, castling):
        from_bit = 1 << sq_from
        to_bit = 1 << sq_to
        moved_piece = self.get_piece(sq_to)
        captured_piece = self.get_piece(sq_from)

        mapping = {
            "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
            "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
        }

        # move piece back
        bb = getattr(self, mapping[moved_piece])
        bb &= ~to_bit
        bb |= from_bit
        setattr(self, mapping[moved_piece], bb)

        # restore captured piece (if any)
        if captured_piece != ".":
            cap_bb = getattr(self, mapping[captured_piece])
            cap_bb |= to_bit
            setattr(self, mapping[captured_piece], cap_bb)

        # restore turn
        self.white_to_move = not self.white_to_move if not castling else self.white_to_move
        return True

    def en_passant_capture_removal(self, sq):
        to_bit = 1 << sq
        for attr in ["wp","bp"]:
            if getattr(self, attr) & to_bit:
                setattr(self, attr, getattr(self, attr) & ~to_bit)
        return True


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