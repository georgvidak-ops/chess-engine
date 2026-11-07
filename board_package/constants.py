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

# mapping that returns wp for P etc.
GLOBAL_MAPPING = {
    "P":"wp","N":"wn","B":"wb","R":"wr","Q":"wq","K":"wk",
    "p":"bp","n":"bn","b":"bb","r":"br","q":"bq","k":"bk"
}