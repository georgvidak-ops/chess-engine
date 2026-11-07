INF = 999_999_999
MAX_PLY = 64
Q_DELTA_MARGIN = 100

# move_score universal values
CAPTURE_MOVE_VALUE = 100_000
KILLER_MOVE_1_SCORE = 90_000
KILLER_MOVE_2_SCORE = 80_000
MAX_QUIET_MOVE_SCORE = 50_000

# tt flags
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

# eval shift types
MOVEMENT = 0
CAPTURE = 1
PROMOTION = 2
# en passant and castling are both variants of movement and capture types