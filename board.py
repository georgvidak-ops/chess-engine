class Board:
    def __init__(self):
        self.init_bitboards()
        self.white_to_move = True
        self.castling_rights = 0b1111 #each bit represents a castling right 1)White short, 2)White long, 3)Black short, 4)Black long

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

    def bishop_moves(self, sq, own, enemy):
        moves = 0

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

                if bit & own:
                    break

                moves |= bit

                if bit & enemy:
                    break

        return moves

    def BishopValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.bishop_moves(sq_from, own, enemy)
        return bool(moves & (1 << sq_to))
    
    # -------------------------
    # ROOK
    # -------------------------
    def rook_moves(self, sq, own, enemy):
        moves = 0

        #veritcal check
        for d in [8, -8]:
            s = sq

            while True:
                prev = s
                s += d

                if s < 0 or s > 63:
                    break

                bit = 1 << s

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

                if bit & own:
                    break

                moves |= bit

                if bit & enemy:
                    break

        return moves
    
    def RookValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.rook_moves(sq_from, own, enemy)

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
    
    def queen_moves(self, sq, own, enemy):
        return self.rook_moves(sq, own, enemy) + self.bishop_moves(sq, own, enemy)

    def QueenValidity(self, sq_from, sq_to, clr):
        own = self.white if clr else self.black
        enemy = self.black if clr else self.white

        moves = self.queen_moves(sq_from, own, enemy)
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
    # PAWN
    # -------------------------

    def pawnValidity(self, sq_from, sq_to, clr):
        occ = self.occupied

        direction = -8 if clr else 8
        start_rank = 6 if clr else 1
        cap_dir_one = -9 if clr else 9
        cap_dir_two = -7 if clr else 7

        r1, f1 = divmod(sq_from, 8)
        r2, f2 = divmod(sq_to, 8)

        target = 1 << sq_to

        # forward move
        if f1 == f2:
            if sq_to == sq_from + direction and not (target & occ):
                return True

            if r1 == start_rank and sq_to == sq_from + 2 * direction:
                mid = sq_from + direction
                if not ((1 << mid) & occ) and not (target & occ):
                    return True

        # capture
        if abs(f1 - f2) == 1 and (sq_to == sq_from + cap_dir_one) or (sq_to == sq_from + cap_dir_two):
            enemy = self.black if clr else self.white
            if target & enemy:
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