from board import Board

def main():
    board = Board()
    
    while True:
        board.print_board()
        
        move = input("Enter move (e.g. e2e4) or 'q' to quit: ")
        
        if move == "q":
            break
        
        # for now, just print it (we’ll validate later)
        print(f"You entered: {move}")

if __name__ == "__main__":
    main()