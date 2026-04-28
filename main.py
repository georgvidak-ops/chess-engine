from board import Board

def main():
    board = Board()
    turn = True #true = white to play, false = black to play

    while True:
        board.print_board()
        
        move = input("Enter move (e.g. e2e4) or 'q' to quit: ")
        
        if move == "q":
            break
        
        f_file, f_rank, t_file, t_rank = move

        if board.checkValidity(f_rank, f_file, t_rank, t_file, turn):
            print("Valid Move")
            turn = not turn
            board.makeMove(f_rank, f_file, t_rank, t_file)
        else:
            print("Invalid Move")
            break


if __name__ == "__main__":
    main()