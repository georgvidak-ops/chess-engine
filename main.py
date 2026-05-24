from board import Board
from machine import Machine

def main():
    board = Board()
    engine = Machine(board)

    #print(board.perft(1, True))   # 20
    #print(board.perft(2, True))   # 400
    #print(board.perft(3, True))   # 8,902
    #print(board.perft(4, True))   # 197,281

    while True:
        if board.white_to_move: # human vs ai

            board.print_board()
            board.castling = False
            print("King is in check") if board.king_in_check(board.white_to_move) else print("King is Safe")
            moves = len(board.generate_legal_moves(board.white_to_move))
            print("Legal moves:", moves)
            if moves == 0:
                if board.king_in_check(board.white_to_move):
                    print("Checkmate!")
                    break
                else:
                    print("Stalemate!")
                    break

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

        else:
            board.print_board()
            move = engine.find_best_move(4)
            sq_from, sq_to = move
            print(engine.evaluate())
            board.makeMove_sq(sq_from, sq_to, False)


if __name__ == "__main__":
    main()