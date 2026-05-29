class Board:
    def __init__(self):
        self.init_bitboards()
        self.white_to_move = True
        self.castling_rights = 0b1111 #each bit represents a castling right 1)White short, 2)White long, 3)Black short, 4)Black long
        self.en_passant_square = 0
        self.captured_piece = "."
        self.just_promoted = False
        self.move_stack = []

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

        if not bool(moves & (1 << sq_to)): return False

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

        return attacks & 0xFFFFFFFFFFFFFFFF #64 bit masking
    
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

        return attacks & 0xFFFFFFFFFFFFFFFF
    
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
        enemy_attack_board = self.pawn_attacks(None, not clr) | self.knight_attacks(None, not clr) | self.bishop_attacks(None, not clr) | self.rook_attacks(None, not clr) | self.queen_attacks(None, not clr) | self.king_attacks(not clr)
        king = self.wk if clr else self.bk
        if king & enemy_attack_board:
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

        return moves & 0xFFFFFFFFFFFFFFFF
    
    def legal_move_castling(self, clr):
        legal_castles = []
        from_sq = 60 if clr else 4 # king square based on colour
        to_sq_short = 62 if clr else 6
        to_sq_long = 58 if clr else 2

        pieces_short = [61, 62] if clr else [5, 6]
        pieces_long = [57, 58, 59] if clr else [1, 2, 3]

        can_s = True # ability to castle short based solely on occupied squares
        can_l = True # ability to castle long based solely on occupied squares
        for piece in pieces_short:
            if (1 << piece) & self.occupied:
                can_s = False
        for piece in pieces_long:
            if (1 << piece) & self.occupied:
                can_l = False

        mask_s = 0b1000 if clr else 0b0010
        mask_l = 0b0100 if clr else 0b0001

        if can_s and self.castling_rights & mask_s:
            legal_castles.append((from_sq, to_sq_short))
        if can_l and self.castling_rights & mask_l:
            legal_castles.append((from_sq, to_sq_long))

        return legal_castles

    
    def generate_legal_moves(self, clr):
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
                    moves = self.king_attacks(clr) & ~own

                # iterate targets
                while moves:
                    to_bit = moves & -moves
                    to_sq = to_bit.bit_length() - 1
                    moves &= moves - 1

                    # make move
                    self.makeMove_sq(from_sq, to_sq)

                    # legality check
                    if not self.king_in_check(clr):
                        legal_moves.append((from_sq, to_sq))

                    # undo move
                    self.unmakeMove_sq(from_sq, to_sq)

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
    
    def promotion(self, sq, making): # making == True means the program is making a move, False means unmaking
        clr = self.white_to_move if making else not self.white_to_move
        queen_bb = self.wq if clr else self.bq
        pawn_bb = self.wp if clr else self.bp
        if making:
            pawn_bb &= ~(1 << sq)
            queen_bb |= (1 << sq)
        else:
            queen_bb &= ~(1 << sq)
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
                self.castling_rights &= ~0b0001
            elif sq_from == 0:
                self.castling_rights &= ~0b0010

    def castle(self, sq_from, sq_to, making):
        piece = self.get_piece(sq_from if making else sq_to)
        clr = piece.isupper()
        short = sq_to > sq_from
        r = 0
        if clr and short:
            r = self.parse("h1f1") if making else self.parse("f1h1")
        elif clr and not short:
            r = self.parse("a1d1") if making else self.parse("d1a1")
        elif not clr and short:
            r = self.parse("h8f8") if making else self.parse("f8h8")
        elif not clr and not short: 
            r = self.parse("a8d8") if making else self.parse("d8a8")

        from_sq, to_sq = r
        if not making:
            self.unmakeMove_sq(to_sq, from_sq, True)
            return True
        if (sq_from, sq_to) in self.legal_move_castling(clr):
            if making:
                self.makeMove_sq(from_sq, to_sq, True)
            return True
        else:
            print("Cant castle")
            return False


    # -------------------------
    # MAKE MOVE
    # -------------------------

    def makeMove_sq(self, sq_from, sq_to, castling=False):
        piece = self.get_piece(sq_from)
        old_en_passant_square = 0
        if abs(sq_to - sq_from) == 2 and piece.lower() == "k":
            if not self.castle(sq_from, sq_to, True): print("Idiot")
           
        if piece == ".":
            return False
        
        old_castling_rights = self.castling_rights
        self.castling_rights_modify(piece, sq_from)

        from_bit = 1 << sq_from
        to_bit = 1 << sq_to

        self.just_promoted = False
        old_en_passant_square = self.en_passant_square

        # en_passant_square reset
        if not (abs(sq_from - sq_to) == 16 and piece.lower() == "p"): # double pawn push
            self.en_passant_square = 0

        self.captured_piece = "."
        # capture removal
        for attr in ["wp","wn","wb","wr","wq","wk","bp","bn","bb","br","bq","bk"]:
            if getattr(self, attr) & to_bit:
                self.captured_piece = attr
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

        if piece.lower() == "p" and sq_to // 8 in (0,7):
            self.just_promoted = True
            self.promotion(sq_to, True)

        if castling: return True #when the rook move of castling takes place, dont save it in the stack
        self.white_to_move = not self.white_to_move

        # move stacking in memory
        moved_piece = piece
        captured_piece = self.captured_piece
        promotion_happened = self.just_promoted
        old_white_to_move_after = self.white_to_move

        move_state = (
            moved_piece,
            captured_piece,
            old_en_passant_square,
            old_castling_rights,
            promotion_happened,
            old_white_to_move_after,
        )
        self.move_stack.append(move_state)
        return True
    
    def unmakeMove_sq(self, sq_from, sq_to, castling=False):
        moved_piece, old_en_passant_square, old_castling_rights, promotion_happened, old_white_to_move_after = (0,0,0,0,0)
        captured_piece = "."
        # restore saved move state
        if not castling:
            (
                moved_piece,
                captured_piece,
                old_en_passant_square,
                old_castling_rights,
                promotion_happened,
                old_white_to_move_after,
            ) = self.move_stack.pop()
        else:
            moved_piece = self.get_piece(sq_to)

        if abs(sq_to - sq_from) == 2 and moved_piece.lower() == "k":
            self.castle(sq_from, sq_to, False)
        from_bit = 1 << sq_from
        to_bit = 1 << sq_to

        mapping = {
            "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
            "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
        }

        # undo promotion
        if moved_piece.lower() == "p" and sq_to // 8 in (0,7) and promotion_happened:
            self.promotion(sq_to, False)

        # move piece back
        bb = getattr(self, mapping[moved_piece])
        bb &= ~to_bit
        bb |= from_bit
        setattr(self, mapping[moved_piece], bb)

        # restore captured piece
        if captured_piece != ".":
            cap_bb = getattr(self, captured_piece)

            cap_bb |= to_bit

            setattr(self, captured_piece, cap_bb)

        # restore game state
        if castling: return True

        self.en_passant_square = old_en_passant_square

        self.castling_rights = old_castling_rights

        self.white_to_move = not old_white_to_move_after

        return True

    def en_passant_capture_removal(self, sq):
        to_bit = 1 << sq
        for attr in ["wp","bp"]:
            if getattr(self, attr) & to_bit:
                setattr(self, attr, getattr(self, attr) & ~to_bit)
        return True
    
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