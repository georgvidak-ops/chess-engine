from board import Board
from machine import Machine
import cProfile
import pstats

profiler = cProfile.Profile()

def snapshot(board):
    return (
        board.wp, board.wn, board.wb, board.wr, board.wq, board.wk,
        board.bp, board.bn, board.bb, board.br, board.bq, board.bk,
        board.white_to_move,
        board.castling_rights,
        board.en_passant_square,
        board.hash
    )

def test_make_unmake():
    board = Board()

    moves = board.generate_pseudo_moves(board.white_to_move)

    for move in moves:
        before = snapshot(board)

        board.makeMove_sq(*move)

        # You can also validate the position here
        board.unmakeMove_sq(*move)

        after = snapshot(board)

        if before != after:
            print("FAILED:", move)
            raise AssertionError("Board changed after make/unmake")

    print("make/unmake test passed")


def validate_board(board):
    pieces = [
        board.wp, board.wn, board.wb,
        board.wr, board.wq, board.wk,
        board.bp, board.bn, board.bb,
        board.br, board.bq, board.bk
    ]

    occupied = 0

    for bb in pieces:
        if occupied & bb:
            raise AssertionError("Two pieces occupy the same square")

        occupied |= bb

    if occupied.bit_count() > 64:
        raise AssertionError("Invalid occupancy")
    
    print("Board Validated")

def snapshotcomp(before, after):
    if before != after:
        print("SEARCH CORRUPTED BOARD")

        names = [
            "wp", "wn", "wb", "wr", "wq", "wk",
            "bp", "bn", "bb", "br", "bq", "bk",
            "white_to_move",
            "castling_rights",
            "en_passant_square",
            "hash"
        ]

        for name, a, b in zip(names, before, after):
            if a != b:
                print(name)
                print(" BEFORE:", a)
                print(" AFTER: ", b)

        raise AssertionError("Search corrupted board")

    print("Search integrity test passed")


def board_bottleneck_profiling():
    board = Board()
    machine = Machine(board)

    before = snapshot(board)
    profiler.enable()

    machine.find_best_move(6)

    profiler.disable()
    after = snapshot(board)

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime")
    stats.print_stats(30)

    snapshotcomp(before, after)
    board.print_board()

def speed_benchmark():
    board = Board()
    machine = Machine(board)

    before = snapshot(board)

    machine.find_best_move(6)

    after = snapshot(board)

    snapshotcomp(before, after)
    board.print_board()

def count_pieces(piece):
    return bin(piece).count('1')

def exception_raiser(board, piece, name, num):
    if count_pieces(piece) > num:
            print(piece)
            board.print_board()
            raise Exception(name, " exception")

speed_benchmark() # function searches the first move at depth 6 and is used as a benchmark for speed after each update