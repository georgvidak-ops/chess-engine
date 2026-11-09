from board_package import Board
from engine import Engine
from engine.evaluation import evaluate
from board_package.attacks import is_king_attacked
from board_package.move_validation import check_validity_sq
from board_package.move_execution import makeMove_sq, unmakeMove_sq
from board_package.move_generation import generate_legal_moves

def main():
    board = Board()
    engine = Engine(board)

    print("-------------------------------------------")
    print("STORMFISH\nA Python Chess Engine")
    print("Enter moves in the format: e2e4\nas well as O-O for kingside castling and O-O-O for queenside castling")
    print("-------------------------------------------\n\n")

    while True:
        if board.white_to_move: # human vs ai

            board.print_board()

            if is_king_attacked(board, board.white_to_move): print("King is in check")
            moves = len(generate_legal_moves(board, board.white_to_move))
            print("Legal moves:", moves)
            if moves == 0:
                if is_king_attacked(board, board.white_to_move):
                    print("Checkmate!")
                    break
                else:
                    print("Stalemate!")
                    break

            def avoid_check(sq_from, sq_to, clr):
                if is_king_attacked(board, clr):
                    unmakeMove_sq(board, sq_from, sq_to)
                    print("Invalid move, king will be captured")
                    return True
                return False

            move = input("Enter move (e.g. e2e4) (or enter q to quit the program): ")

            if move == "q":
                break

            if len(move) != 4:
                if move == "O-O":
                    sq_from, sq_to = (60, 62) if board.white_to_move else (4, 6)
                    makeMove_sq(board, sq_from, sq_to)
                    continue
                elif move == "O-O-O":
                    sq_from, sq_to = (60, 58) if board.white_to_move else (4, 2)
                    makeMove_sq(board, sq_from, sq_to)
                    continue
                print("Wrong format")
                continue

            sq_from, sq_to = board.parse(move)

            if check_validity_sq(board, sq_from, sq_to):
                board.principal_variation.append((sq_from, sq_to))
                makeMove_sq(board,sq_from, sq_to)
                if avoid_check(sq_from, sq_to, not board.white_to_move):
                    continue
                print("Valid move")
            else:
                print("Invalid move, try again")
                continue

        else:
            board.print_board()
            move = engine.find_best_move(6)
            if move == None: break
            sq_from, sq_to = move
            print(evaluate(board))
            makeMove_sq(board, sq_from, sq_to)


if __name__ == "__main__":
    main()