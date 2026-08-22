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
            print("King is in check") if board.is_king_attacked(board.white_to_move) else print("King is Safe")
            moves = len(board.generate_legal_moves(board.white_to_move))
            print("Legal moves:", moves)
            if moves == 0:
                if board.is_king_attacked(board.white_to_move):
                    print("Checkmate!")
                    break
                else:
                    print("Stalemate!")
                    break

            def avoid_check(sq_from, sq_to, clr):
                if board.is_king_attacked(clr):
                    board.unmakeMove_sq(sq_from, sq_to)
                    print("Invalid move, king will be captured")
                    return True
                return False

            move = input("Enter move (e.g. e2e4) (or enter q to quit the program): ")

            if move == "q":
                break

            if len(move) != 4:
                if move == "O-O":
                    sq_from, sq_to = (60, 62) if board.white_to_move else (4, 6)
                    board.makeMove_sq(sq_from, sq_to)
                    continue
                elif move == "O-O-O":
                    sq_from, sq_to = (60, 58) if board.white_to_move else (4, 2)
                    board.makeMove_sq(sq_from, sq_to)
                    continue
                print("Bad format")
                continue

            sq_from, sq_to = board.parse(move)

            if board.checkValidity_sq(sq_from, sq_to):
                board.makeMove_sq(sq_from, sq_to)
                if avoid_check(sq_from, sq_to, not board.white_to_move):
                    continue
                print("Valid move")
            else:
                print("Invalid move")
                continue

        else:
            board.print_board()
            move = engine.find_best_move(8)
            if move == None: break
            sq_from, sq_to = move
            print(engine.evaluate())
            board.makeMove_sq(sq_from, sq_to)


if __name__ == "__main__":
    main()