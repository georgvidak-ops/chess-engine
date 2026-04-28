from board import Board

def main():
    board = Board()

    while True:
        board.print_board()

        move = input("Enter move (e.g. e2e4): ")

        if move == "q":
            break

        if len(move) != 4:
            print("Bad format")
            continue

        sq_from, sq_to = board.parse(move)

        if board.checkValidity_sq(sq_from, sq_to):
            board.makeMove_sq(sq_from, sq_to)
            print("Valid move")
        else:
            print("Invalid move")
            break


if __name__ == "__main__":
    main()