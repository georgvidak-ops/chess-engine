from .constants import (
    MASK_64,
    ROOK_RAYS,
    BISHOP_RAYS,
    SQUARES_ALIGNED,
    RAY_BETWEEN,
    RAY_LINE,
    STRAIGHT,
    DIAGONAL,
    NOT_A_FILE,
    NOT_H_FILE,
    NOT_AB_FILE,
    NOT_GH_FILE
)

# -------------------------
# INIT POSITION
# -------------------------
def init_rays():
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

def init_alignment_table(): # first 64 
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

def init_between_rays():
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

def init_ray_line():
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

def raycast_attacks(board, sq, dirs, enemy_bb, raycasts = False):
    rays = ROOK_RAYS[sq] if dirs == STRAIGHT else BISHOP_RAYS[sq]
    full_rays = ROOK_RAYS if dirs == STRAIGHT else BISHOP_RAYS

    occupied = board.occupied
    attacks = 0

    if dirs == STRAIGHT:
        msb_dirs = (True, False, False, True) # N, E, S, W
    else:
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
    

def pawn_attacks(board, from_sq, clr):
    pawns = board.wp if clr else board.bp
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
def knight_attacks(board, from_sq, clr):
    knights = board.wn if clr else board.bn
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

def rook_attacks(board, from_sq, clr):
    rooks = board.wr if clr else board.br
    if from_sq != None:
        rooks = 1 << from_sq

    enemy = board.black if clr else board.white
    squares = board.extract_squares(rooks)
    attacks = 0
    for i in squares:
        attacks |= raycast_attacks(board, i, STRAIGHT, enemy, False)
    return attacks

def bishop_attacks(board, from_sq, clr):
    bishops = board.wb if clr else board.bb
    if from_sq != None:
        bishops = 1<< from_sq

    enemy = board.black if clr else board.white
    squares = board.extract_squares(bishops)
    attacks = 0
    for i in squares:
        attacks |= raycast_attacks(board, i, DIAGONAL, enemy, False)
    return attacks

def queen_attacks(board, from_sq, clr):
    queens = board.wq if clr else board.bq
    if from_sq != None:
        queens = 1 << from_sq

    enemy = board.black if clr else board.white
    squares = board.extract_squares(queens)
    attacks = 0
    for i in squares:
        attacks |= (raycast_attacks(board, i, STRAIGHT, enemy, False) | raycast_attacks(board, i, DIAGONAL, enemy, False))
    return attacks

def king_attacker(board, clr):
    king = board.wk if clr else board.bk
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

def pawn_attackers(sq, clr): #clr of the attacker
    target = 1 << sq

    if clr:
        # White pawns attack upwards, so reverse the attack.
        return ((target << 7) & NOT_H_FILE) | ((target << 9) & NOT_A_FILE)
    else:
        # Black pawns attack downwards.
        return ((target >> 7) & NOT_A_FILE) | ((target >> 9) & NOT_H_FILE)

def knight_attackers(board, sq):
    if sq == -1:
        board.print_board() # debugging log
        print(board.principal_variation)
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

def is_king_attacked(board, clr):
    enemy = board.black if clr else board.white
    own_king = board.wk if clr else board.bk
    knights = board.bn if clr else board.wn
    pawns = board.bp if clr else board.wp
    rooks = board.br if clr else board.wr
    queens = board.bq if clr else board.wq
    bishops = board.bb if clr else board.wb

    king_sq = own_king.bit_length() - 1

    if knight_attackers(board, king_sq) & knights:
        return True
    if king_attacker(board, clr) & own_king:
        return True
    if pawn_attackers(king_sq, not clr) & pawns:
        return True
    if raycast_attacks(board, king_sq, STRAIGHT, enemy, False) & (rooks | queens): # rook_moves
        return True
    if raycast_attacks(board, king_sq, DIAGONAL, enemy, False) & (bishops | queens): # bishop_moves
        return True
    return False

def gives_check(board, clr, sq_from, sq_to):
    enemy = board.black if clr else board.white

    king_bit = board.bk if clr else board.wk
    king_sq = king_bit.bit_length() - 1

    piece = board.get_piece(sq_to)

    direct_attacks = 0

    if piece.upper() == 'P':
        direct_attacks = pawn_attackers(sq_to, clr)
    elif piece.upper() == 'N':
        direct_attacks = knight_attackers(board, sq_to)
    elif piece.upper() == 'B':
        direct_attacks = raycast_attacks(board, sq_to, DIAGONAL, enemy, False) #bishop_moves
    elif piece.upper() == 'R':
        direct_attacks = raycast_attacks(board, sq_to, STRAIGHT, enemy, False) #rook_moves
    elif piece.upper() == 'Q':
        direct_attacks = raycast_attacks(board, sq_to, STRAIGHT, enemy, False) | raycast_attacks(board, sq_to, DIAGONAL, enemy, False) #queen moves
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
        return is_discovered_check(board, sq_from, sq_to, clr, piece)

    return False

def is_discovered_check(board, sq_from, sq_to, clr, piece):
    enemy_king_sq = board.bk.bit_length() - 1 if clr else board.wk.bit_length() - 1

    if piece.upper() == "K":
        return is_king_attacked(board, not clr)
        
    # if sq_to stays on the same ray the moving piece still blocks the check
    if SQUARES_ALIGNED[sq_to][enemy_king_sq] and (RAY_LINE[sq_from][enemy_king_sq] == RAY_LINE[sq_to][enemy_king_sq]):
        return False

    # find own sliders behind sq_from along the king ray
    full_ray = RAY_LINE[sq_from][enemy_king_sq]
    
    own_sliders = (board.wq | board.wr | board.wb) if clr else (board.bq | board.br | board.bb)
    potential_attackers = own_sliders & full_ray
    
    if not potential_attackers:
        return False

    # verify sq_from was the only piece between a slider and the king
    for attacker_sq in board.extract_squares(potential_attackers):
        # make sure slider is behind sq_from relative to the king
        if (1 << sq_from) & RAY_BETWEEN[attacker_sq][enemy_king_sq]:
            # check if other piece blocks the path
            between_mask = RAY_BETWEEN[attacker_sq][enemy_king_sq] & ~(1 << sq_from)
            # handle en passant captured pawn removal from ray
            if piece.upper() == 'P' and sq_to == board.en_passant_square:
                ep_pawn_sq = sq_to - 8 if clr else sq_to + 8
                between_mask &= ~(1 << ep_pawn_sq)
            if (between_mask & board.occupied) == 0:
                # check if piece type matches ray direction (Diagonal or Straight)
                if valid_slider_for_ray(board, attacker_sq, enemy_king_sq):
                    return True

    return False

def valid_slider_for_ray(board, sq, king_sq):
    if sq % 8 == king_sq % 8 or sq // 8 == king_sq // 8:
        # straight slider
        return (board.get_piece(sq).upper() in ("R", "Q"))
    else:
        # diagonal slider
        return (board.get_piece(sq).upper() in ("B", "Q"))