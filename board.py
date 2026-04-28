class Board:
    def __init__(self):
        self.board = self.create_starting_board()


    def checkValidity(self, r1, f1, r2, f2):
        board = self.board

        # file conversion: a-h → 0-7
        f1 = ord(f1) - ord('a')
        f2 = ord(f2) - ord('a')

        # rank conversion: '1'-'8' → 7-0
        r1 = 8 - int(r1)
        r2 = 8 - int(r2)

        color = (board[r1][f1]).isupper() # white = true, black = false

        if not (all(0 <= x <= 7 for x in (r1, f1, r2, f2))):
            return False

        if board[r1][f1] == "p" or board[r1][f1] == "P": # Pawn Check
            return self.pawnValidity(r1, f1, r2, f2, color)


    def pawnValidity(self, r1, f1, r2, f2, clr):
        board = self.board
        step = 1

        if (clr and r1 == 6) or (not clr and r1 == 1): #check if pawn has moved to see if we can move it 2 squares or not
            step = 2

        target = board[r2][f2]

        if (f1 == f2) and target == "." and abs(r2 - r1) <= step: #check if move is valid in terms of the piece being a pawn
            if abs(r2 - r1) == 2:
                if (clr and board[r1-1][f1] != ".") or (not clr and board[r1+1][f1] != "."): #check if we jumped over pieces when moving the pawn 2 squares
                    return False
            if (clr and (r2 - r1) < 0) or (not clr and (r2 - r1) > 0): #check if move is valid given the color
                return True
        elif abs(f1 - f2) == 1 and target != "." and target.isupper() != clr and abs(r2 - r1) == 1: #check if move is valid in terms of the piece being a pawn
            if (clr and (r2 - r1) < 0) or (not clr and (r2 - r1) > 0): #check if move is valid given the colour
                return True
        #no en passant yet
        return False


    def makeMove(self, r1, f1, r2, f2):
        board = self.board

        # file conversion: a-h → 0-7
        f1 = ord(f1) - ord('a')
        f2 = ord(f2) - ord('a')

        # rank conversion: '1'-'8' → 7-0
        r1 = 8 - int(r1)
        r2 = 8 - int(r2)

        board[r2][f2] = board[r1][f1]
        board[r1][f1] = "."


    def create_starting_board(self):
        return [
            ["r","n","b","q","k","b","n","r"],
            ["p","p","p","p","p","p","p","p"],
            [".",".",".",".",".",".",".","."],
            [".",".",".",".",".",".",".","."],
            [".",".",".",".",".",".",".","."],
            [".",".",".",".",".",".",".","."],
            ["P","P","P","P","P","P","P","P"],
            ["R","N","B","Q","K","B","N","R"],
        ]

    def print_board(self):
        for row in self.board:
            print(" ".join(row))
        print()