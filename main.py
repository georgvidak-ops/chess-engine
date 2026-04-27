from board import Board

def main():
    board = Board()
    
    while True:
        board.print_board()
        
        move = input("Enter move (e.g. e2e4) or 'q' to quit: ")
        
        if move == "q":
            break
        
        f_file, f_rank, t_file, t_rank = move

        board.makeMove(f_rank, f_file, t_rank, t_file)


if __name__ == "__main__":
    main()