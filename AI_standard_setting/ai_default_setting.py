import numpy as np
from game_setup.chess_rule import GamePosition, Move

DEPTH = 1

Piece_to_Value = {'wK': 0, 'wP': 1, 'wN': 3, 'wB': 3, 'wR': 5, 'wQ': 9,
                  'bK': 0, 'bP': -1, 'bN': -3, 'bB': -3, 'bR': -5, 'bQ': -9, '--' : 0}

Knight_positional_value = np.array([[1, 2, 3, 3, 3, 3, 2, 1],
                                    [2, 3, 4, 4, 4, 4, 3, 2],
                                    [3, 4, 4, 5, 5, 4, 4, 3],
                                    [3, 4, 5, 5, 5, 5, 4, 3],
                                    [3, 4, 5, 5, 5, 5, 4, 3],
                                    [3, 4, 4, 5, 5, 4, 4, 3],
                                    [2, 3, 4, 4, 4, 4, 3, 2],
                                    [1, 2, 3, 3, 3, 3, 2, 1]])

Bishop_positional_value = np.array([[6, 5, 4, 3, 3, 4, 5, 6],
                                    [5, 6, 5, 4, 4, 5, 6, 5],
                                    [4, 5, 6, 5, 5, 6, 5, 4],
                                    [3, 4, 5, 6, 6, 5, 4, 3],
                                    [3, 4, 5, 6, 6, 5, 4, 3],
                                    [4, 5, 6, 5, 5, 6, 5, 4],
                                    [5, 6, 5, 4, 4, 5, 6, 5],
                                    [6, 5, 4, 3, 3, 4, 5, 6]])

Queen_positional_value = np.zeros((8,8))

Rook_positional_value = np.zeros((8,8))

King_positional_value = np.zeros((8,8))

White_pawn_positional_value = np.array([[9, 9, 9, 9, 9, 9, 9, 9],
                                        [6, 6, 6, 6, 6, 6, 6, 6],
                                        [5, 5, 5, 6, 6, 5, 5, 5],
                                        [4, 4, 5, 5, 5, 5, 4, 4],
                                        [3, 3, 3, 4, 4, 3, 3, 3],
                                        [2, 2, 2, 2, 2, 2, 2, 2],
                                        [1, 1, 1, 1, 1, 1, 1, 1],
                                        [0, 0, 0, 0, 0, 0, 0, 0]])
Black_pawn_positional_value = np.flipud(White_pawn_positional_value)

Piece_to_positional_value = {'wN': Knight_positional_value, 'bN': Knight_positional_value, 'wB': Bishop_positional_value, 'bB': Bishop_positional_value,
                             'wQ': Queen_positional_value, 'bQ': Queen_positional_value, 'wR': Rook_positional_value, 'bR': Rook_positional_value,
                             'wK': King_positional_value, 'bK': King_positional_value, 'wP': White_pawn_positional_value, 'bP': Black_pawn_positional_value}
WIN = 1000
DRAW = 0

def expand_promotions_of_moves(legal_moves, position):
    promotion_pieces = ['Q', 'R', 'B', 'N']
    for i in range(len(legal_moves) - 1, -1, -1):
        if legal_moves[i].is_promotion:
            ally_color = legal_moves[i].piece_move[0]
            start_row = legal_moves[i].start_row
            start_col = legal_moves[i].start_col
            end_row = legal_moves[i].end_row
            end_col = legal_moves[i].end_col
            legal_moves.remove(legal_moves[i])
            for piece in promotion_pieces:
                legal_moves.insert(i,Move((start_row, start_col), (end_row, end_col), position, promotion_piece = ally_color + piece))

def cal_material_score(position):
    r_num = len(position)
    c_num = len(position[1])
    values = np.empty((r_num, c_num))
    for r in range(r_num):
        for c in range(c_num):
            values[r, c] = Piece_to_Value[position[r][c]]
    return np.sum(values)

def evaluate_position(gp, legal_moves):
    if gp.checkmate:
        return -WIN if gp.white_turn else WIN
    elif gp.stalemate:
        return -DRAW if gp.white_turn else -DRAW
    
    r_num = len(gp.position)
    c_num = len(gp.position[1])   
    value= 0
    for r in range(r_num):
        for c in range(c_num):
            sq = gp.position[r][c]
            if sq != '--':
                value += (Piece_to_Value[sq] +  (1 if sq[0] == 'w' else -1) * Piece_to_positional_value[sq][r][c] * .1)
    return np.sum(value)