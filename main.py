from board import Board

def main():
    board = Board()

    while True:
        board.print_board()
        board.castling = False
        print("King is in check") if board.king_in_check(board.white_to_move) else print("King is Safe")

        def avoid_check(sq_from, sq_to, clr):
            if board.king_in_check(clr):
                board.unmakeMove_sq(sq_from, sq_to, False)
                print("Invalid move, king will be captured")
                return True
            return False

        move = input("Enter move (e.g. e2e4) (or enter q to quit the program): ")

        if move == "q":
            break

        if len(move) != 4:
            if move == "O-O":
                if board.CheckCastling(True, board.white_to_move):
                    sq_from, sq_to = board.parse("e1g1") if board.white_to_move else board.parse("e8g8")
                    board.makeMove_sq(sq_from, sq_to, True)
                    if avoid_check(sq_from, sq_to, board.white_to_move): #see if castling is possible (threats)
                        continue
                    sq_from, sq_to = board.parse("h1f1") if board.white_to_move else board.parse("h8f8")
                    board.makeMove_sq(sq_from, sq_to, False)
                    continue
                print("Cant castle short")
                continue
            elif move == "O-O-O":
                if board.CheckCastling(False, board.white_to_move):
                    sq_from, sq_to = board.parse("e1c1") if board.white_to_move else board.parse("e8c8")
                    board.makeMove_sq(sq_from, sq_to, True)
                    if avoid_check(sq_from, sq_to, board.white_to_move): #check if castling is possible (threats)
                        continue
                    sq_from, sq_to = board.parse("a1d1") if board.white_to_move else board.parse("a8d8")
                    board.makeMove_sq(sq_from, sq_to, False)
                    continue
                print("Can castle long")
                continue

            print("Bad format")
            continue

        sq_from, sq_to = board.parse(move)

        if board.checkValidity_sq(sq_from, sq_to):
            board.makeMove_sq(sq_from, sq_to, False)
            if avoid_check(sq_from, sq_to, not board.white_to_move):
                continue

            print("Valid move")
        else:
            print("Invalid move")
            continue


if __name__ == "__main__":
    main()