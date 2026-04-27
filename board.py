# board.py

class Board:
    def __init__(self):
        self.board = self.create_starting_board()

    numsArray = "abcdefgh"

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