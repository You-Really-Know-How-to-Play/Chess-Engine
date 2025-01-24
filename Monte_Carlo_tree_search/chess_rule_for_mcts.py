import copy
import numpy as np

#convert position to np.array and reversely
str_to_vector = {'wK': np.array([1, 0, 0, 0, 0, 0]), 'bK': np.array([-1, 0, 0, 0, 0, 0]),
                'wQ': np.array([0, 1, 0, 0, 0, 0]), 'bQ': np.array([0, -1, 0, 0, 0, 0]),
                'wR': np.array([0, 0, 1, 0, 0, 0]), 'bR': np.array([0, 0, -1, 0, 0, 0]),
                'wN': np.array([0, 0, 0, 1, 0, 0]), 'bN': np.array([0, 0, 0, -1, 0, 0]),
                'wB': np.array([0, 0, 0, 0, 1, 0]), 'bB': np.array([0, 0, 0, 0, -1, 0]),
                'wP': np.array([0, 0, 0, 0, 0, 1]), 'bP': np.array([0, 0, 0, 0, 0, -1]),
                '--': np.array([0, 0, 0, 0, 0, 0])}

def position_to_array(array):
    return list(filter(lambda string: (str_to_vector[string] == array).all(), str_to_vector))[0]


#generate all move ids for nn to select (number of ids: 1968)
def get_move_to_id_map():
    move_to_id = {}
    id_to_move = {}
    idx = 0
    for r in range(8):
        for c in range(8):
            for dir in [(-1,0), (0,-1), (1,0), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                for route in range(1, 8):
                    if (0 <= (r + dir[0] * route) <= 7) and (0 <= (c + dir[1] * route) <= 7):
                        move_to_id[(r, c, r + dir[0] * route, c + dir[1] * route, '?')] = idx
                        id_to_move[idx] = (r, c, r + dir[0] * route, c + dir[1] * route, '?')
                        idx += 1
                    else:
                        break
    for r in range(8):
        for c in range(8):
            for dir in [(1,2), (1,-2), (-1,2), (-1,-2), (2,1), (2,-1), (-2,1), (-2,-1)]:
                if (0 <= (r + dir[0]) <= 7) and (0 <= (c + dir[1]) <= 7):
                    move_to_id[(r, c, r + dir[0], c + dir[1], '?')] = idx
                    id_to_move[idx] = (r, c, r + dir[0], c + dir[1], '?')
                    idx += 1
    for promotion_piece in ['Q', 'R', 'B', 'N']:
        for c in range(8):
            for d in [-1, 0, 1]:
                if 0 <= (c+d) <= 7:
                    move_to_id[(6, c, 7, c+d, promotion_piece)] = idx
                    id_to_move[idx] = (6, c, 7, c+d, promotion_piece)
                    idx += 1
    for promotion_piece in ['Q', 'R', 'B', 'N']:
        for c in range(8):
            for d in [-1, 0, 1]:
                if 0 <= (c+d) <= 7:
                    move_to_id[(1, c, 0, c+d, promotion_piece)] = idx
                    id_to_move[idx] = (1, c, 0, c+d, promotion_piece)
                    idx += 1
    return move_to_id, id_to_move

move_to_id, id_to_move = get_move_to_id_map()

# define the position of the current game, including the previous moves(or not)
class GamePosition():
    def __init__(self):
        self.position = [
            ['bR', 'bN', 'bB', 'bQ', 'bK', 'bB', 'bN', 'bR'],
            ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
            ['wR', 'wN', 'wB', 'wQ', 'wK', 'wB', 'wN', 'wR']]

        self.white_turn = True
        self.checkmate = False
        self.stalemate = False
        self.move_history = []
        self.move_functions = {'P': self.get_pawn_moves, 'R': self.get_rook_moves, 'N': self.get_knight_moves,
                               'B': self.get_bishop_moves, 'Q': self.get_queen_moves, 'K': self.get_king_moves}
        self.white_king_location = (7, 4)
        self.black_king_location = (0, 4)
        self.in_check = False
        self.pins = []
        self.checks = []
        self.en_passant_possible_sq = ()
        self.en_passant_possible_log = [self.en_passant_possible_sq]
        self.current_castling_rights = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(self.current_castling_rights.wks, self.current_castling_rights.bks,
                                               self.current_castling_rights.wqs, self.current_castling_rights.bqs)]
        
        self.pawn_and_cap_move_counter = [0]
        self.position_history=[copy.deepcopy(self.position)] 
        self.fifty_moves_draw = False
        self.three_rep_draw = False

    # change the position using a given normal move(not castling, promotion or en-passant)
    def make_move(self, move):
        self.position[move.start_row][move.start_col] = '--'
        self.position[move.end_row][move.end_col] = move.piece_move
        self.move_history.append(move)
        self.white_turn = not self.white_turn
        # update the kings' locations
        if move.piece_move == 'wK':
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_move == 'bK':
            self.black_king_location = (move.end_row, move.end_col)

        # promotion
        if move.is_promotion:
            self.position[move.end_row][move.end_col] = move.promotion_piece

        # en-passant
        if move.is_en_passant:
            self.position[move.start_row][move.end_col] = '--'
        
        # update the en-passant square
        if move.piece_move[1] == 'P' and abs(move.start_row - move.end_row) == 2:
            self.en_passant_possible_sq = ((move.start_row + move.end_row) // 2, move.start_col)
        else:
            self.en_passant_possible_sq = ()
        self.en_passant_possible_log.append(self.en_passant_possible_sq)

        # castle
        if move.is_castle:
            if move.end_col - move.start_col == 2: # castle short
                self.position[move.end_row][move.end_col - 1] = self.position[move.end_row][move.end_col + 1]
                self.position[move.end_row][move.end_col + 1] = '--'
            else: # castle long
                self.position[move.end_row][move.end_col + 1] = self.position[move.end_row][move.end_col - 2]
                self.position[move.end_row][move.end_col - 2] = '--'
        
        # update the castle rights
        self.update_castle_rights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_rights.wks, self.current_castling_rights.bks,
                                               self.current_castling_rights.wqs, self.current_castling_rights.bqs))
        
        #update the fifty move without pawn move or cap log
        if move.piece_move[1] == 'P' or move.is_cap:
            self.pawn_and_cap_move_counter.append(0)
        else:
            self.pawn_and_cap_move_counter.append(self.pawn_and_cap_move_counter[-1] + 1)

        #update the three rep rule
        self.position_history.append(copy.deepcopy(self.position))

    # undo the last move
    def undo_move(self):
        if len(self.move_history) != 0:
            move = self.move_history.pop()
            self.position[move.start_row][move.start_col] = move.piece_move
            self.position[move.end_row][move.end_col] = move.piece_caped
            self.white_turn = not self.white_turn
            # update the kings' locations
            if move.piece_move == 'wK':
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_move == 'bK':
                self.black_king_location = (move.start_row, move.start_col)
            # undo en passant
            if move.is_en_passant:
                self.position[move.end_row][move.end_col] = '--'
                self.position[move.start_row][move.end_col] = move.piece_caped
                self.en_passant_possible_sq = (move.end_row, move.end_col)
            
            self.en_passant_possible_log.pop()
            self.en_passant_possible_sq = self.en_passant_possible_log[-1]

            # undo the castling rights
            self.castle_rights_log.pop()
            self.current_castling_rights = CastleRights(self.castle_rights_log[-1].wks, self.castle_rights_log[-1].bks,
                                                        self.castle_rights_log[-1].wqs, self.castle_rights_log[-1].bqs)
            
            # undo the castle
            if move.is_castle:
                if move.end_col - move.start_col == 2: # castle short
                    self.position[move.end_row][move.end_col + 1] = self.position[move.end_row][move.end_col - 1]
                    self.position[move.end_row][move.end_col - 1] = '--'
                else:
                    self.position[move.end_row][move.end_col - 2] = self.position[move.end_row][move.end_col + 1]
                    self.position[move.end_row][move.end_col + 1] = '--'

            self.pawn_and_cap_move_counter.pop()
            self.position_history.pop()

            self.checkmate = False
            self.stalemate = False
            self.fifty_moves_draw = False
            self.three_rep_draw = False

    # update the castle rights by a given move
    def update_castle_rights(self, move):
        # if king or rook moves
        if move.piece_move == 'wK':
            self.current_castling_rights.wks = False
            self.current_castling_rights.wqs = False
        elif move.piece_move == 'bK':
            self.current_castling_rights.bks = False
            self.current_castling_rights.bqs = False
        elif move.piece_move == 'wR':
            if move.start_row == 7:
                if move.start_col == 0:
                    self.current_castling_rights.wqs = False
                elif move.start_col == 7:
                    self.current_castling_rights.wks = False
        elif move.piece_move == 'bR':
            if move.start_row == 0:
                if move.start_col == 0:
                    self.current_castling_rights.bqs = False
                elif move.start_col == 7:
                    self.current_castling_rights.bks = False
        # if a rook is caped
        if move.piece_caped == 'wR':
            if move.end_row == 7:
                if move.end_col == 0:
                    self.current_castling_rights.wqs = False
                elif move.end_col == 7:
                    self.current_castling_rights.wks = False
        elif move.piece_caped == 'bR':
            if move.end_row == 0:
                if move.end_col == 0:
                    self.current_castling_rights.bqs = False
                elif move.end_col == 7:
                    self.current_castling_rights.bks = False

    # get all legal moves (i.e. considering checks) for current position
    def get_legal_moves(self, expand_promotions=True, return_ids=False):
        moves = []
        self.in_check, self.checks, self.pins = self.check_pins_and_checks()
        if self.white_turn:
            king_row = self.white_king_location[0]
            king_col = self.white_king_location[1]
        else:
            king_row = self.black_king_location[0]
            king_col = self.black_king_location[1]
        if self.in_check:
            if len(self.checks) == 1:
                moves = self.get_all_moves(expand_all_promotions = expand_promotions)
                check = self.checks[0]
                check_row = check[0]
                check_col = check[1]
                piece_checking = self.position[check_row][check_col]
                vaild_squares = []
                if piece_checking[1] == 'N':
                    vaild_squares = [(check_row, check_col)]
                else:
                    for i in range(1,8):
                        vaild_square = (king_row + check[2] * i, king_col + check[3] * i)
                        vaild_squares.append(vaild_square)
                        if vaild_square[0] == check_row and vaild_square[1] == check_col:
                            break
                for i in range(len(moves) - 1, -1, -1):
                    if moves[i].piece_move[1] != 'K':
                        if not (moves[i].end_row, moves[i].end_col) in vaild_squares:
                            moves.remove(moves[i])
            else:
                self.get_king_moves(king_row, king_col, moves)
        else:
            moves = self.get_all_moves(expand_all_promotions = expand_promotions)


        #check win and draw
        if len(moves) == 0:
            if self.in_check:
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        if self.pawn_and_cap_move_counter[-1] >= 50:
            self.fifty_moves_draw = True
        same_position_counter = 0

        for pos in self.position_history:
            if self.position == pos:
                same_position_counter += 1
        if same_position_counter >= 3:
            self.three_rep_draw = True

        if return_ids:
            legal_move_ids = []
            for i in range(len(moves)):
                legal_move_ids.append(move_to_id[(moves[i].start_row, moves[i].start_col, moves[i].end_row, moves[i].end_col, moves[i].promotion_piece[-1])])
            return legal_move_ids
        else:
            return moves
    
    # get all possible moves (i.e. without considering checks) for current position
    def get_all_moves(self, expand_all_promotions = True):
        moves = []
        for r in range(len(self.position)):
            for c in range(len(self.position[r])):
                color = self.position[r][c][0]
                if (color == 'w' and self.white_turn) or (color == 'b' and not self.white_turn):
                    piece = self.position[r][c][1]
                    if piece != 'P':
                        self.move_functions[piece](r, c, moves)
                    else:
                        self.move_functions[piece](r, c, moves, expand_promotions = expand_all_promotions)

        return moves

    # given a pawn, generate all possible moves and attend them to the list moves
    def get_pawn_moves(self, r, c, moves, expand_promotions = True):
        piece_pinned = False
        pin_dir = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piece_pinned = True
                pin_dir = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        
        if self.white_turn:
            ally_color = 'w'
            enemy_color = 'b'
            front_dir = -1
            promotion_row = 0
            start_row = 6
        else:
            ally_color = 'b'
            enemy_color = 'w'
            front_dir = 1
            promotion_row = 7
            start_row = 1

        if self.position[r + front_dir][c] == '--': # advance
            if not piece_pinned or pin_dir == (front_dir, 0):
                if r + front_dir == promotion_row and expand_promotions:
                    for promotion_piece in ['Q', 'R', 'B', 'N']:
                        moves.append(Move((r, c), (r + front_dir, c), self.position, promotion_piece = ally_color + promotion_piece))
                else:
                    moves.append(Move((r, c), (r + front_dir, c), self.position))
                if r == start_row and self.position[r + 2 * front_dir][c] == '--':
                    moves.append(Move((r, c), (r + 2 * front_dir, c), self.position))
        for cap_dir in [-1, 1]: #capture
            if 0 <= c + cap_dir <= 7:
                if self.position[r+front_dir][c+cap_dir][0] == enemy_color:
                    if not piece_pinned or pin_dir == (front_dir, cap_dir):
                        if r + front_dir == promotion_row and expand_promotions:
                            for promotion_piece in ['Q', 'R', 'B', 'N']:
                                moves.append(Move((r, c), (r + front_dir, c + cap_dir), self.position, promotion_piece = ally_color + promotion_piece))
                        else:
                            moves.append(Move((r, c), (r + front_dir, c + cap_dir), self.position))
                elif (r + front_dir, c + cap_dir) == self.en_passant_possible_sq:
                    self.position[r+front_dir][c+cap_dir] = ally_color + 'P'
                    self.position[r][c] = '--'
                    self.position[r][c+cap_dir] = '--' 
                    in_check, temp1, temp2 = self.check_pins_and_checks()
                    self.position[r+front_dir][c+cap_dir] = '--'
                    self.position[r][c] = ally_color + 'P'
                    self.position[r][c+cap_dir] = enemy_color + 'P' 
                    if not in_check:
                        moves.append(Move((r, c), (r + front_dir, c + cap_dir), self.position, is_en_passant = True))
    '''             
            if c + 1 <= 7: # capture to the right
                if self.position[r-1][c+1][0] == 'b':
                    if not piece_pinned or pin_dir == (-1, 1):
                        moves.append(Move((r, c), (r - 1, c + 1), self.position))
                elif (r-1,c+1) == self.en_passant_possible_sq:
                    self.position[r-1][c+1] = 'wP'
                    self.position[r][c] = '--'
                    self.position[r][c+1] = '--' 
                    in_check, temp1, temp2 = self.check_pins_and_checks()
                    self.position[r-1][c+1] = '--'
                    self.position[r][c] = 'wP'
                    self.position[r][c+1] = 'bP'  
                    if not in_check:
                        moves.append(Move((r, c), (r - 1, c + 1), self.position, is_en_passant = True))
                                    
        else: # black's turn
            if self.position[r+1][c] == '--': # advance
                if not piece_pinned or pin_dir == (1, 0):
                    moves.append(Move((r, c), (r + 1, c), self.position))
                    if r == 1 and self.position[r+2][c] == '--':
                        moves.append(Move((r, c), (r + 2, c), self.position))
            if c - 1 >= 0: # capture to the left 
                if self.position[r+1][c-1][0] == 'w':
                    if not piece_pinned or pin_dir == (1, -1):
                        moves.append(Move((r, c), (r + 1, c - 1), self.position))
                elif (r+1,c-1) == self.en_passant_possible_sq:
                    self.position[r+1][c-1] = 'bP'
                    self.position[r][c] = '--'
                    self.position[r][c-1] = '--' 
                    in_check, temp1, temp2 = self.check_pins_and_checks()
                    self.position[r+1][c-1] = '--'
                    self.position[r][c] = 'bP'
                    self.position[r][c-1] = 'wP' 
                    if not in_check:
                        moves.append(Move((r, c), (r + 1, c - 1), self.position, is_en_passant = True))
                    
            if c + 1 <= 7: # capture to the right
                if self.position[r+1][c+1][0] == 'w':
                    if not piece_pinned or pin_dir == (1, 1):
                        moves.append(Move((r, c), (r + 1, c + 1), self.position))
                elif (r+1,c+1) == self.en_passant_possible_sq:
                    self.position[r+1][c+1] = 'bP'
                    self.position[r][c] = '--'
                    self.position[r][c+1] = '--' 
                    in_check, temp1, temp2 = self.check_pins_and_checks()
                    self.position[r+1][c+1] = '--'
                    self.position[r][c] = 'bP'
                    self.position[r][c+1] = 'wP'
                    if not in_check:
                        moves.append(Move((r, c), (r + 1, c + 1), self.position, is_en_passant = True))
    '''                                
    # given a rook, generate all possible moves and attend them to the list moves
    def get_rook_moves(self, r, c, moves):
        piece_pinned = False
        pin_dir = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piece_pinned = True
                pin_dir = (self.pins[i][2], self.pins[i][3])
                if self.position[r][c][1] != 'Q':
                    self.pins.remove(self.pins[i])
                break

        for dir in [(0,1), (0, -1), (1, 0), (-1, 0)]: # check 4 directions
            if not piece_pinned or pin_dir == dir or pin_dir == (-dir[0], -dir[1]):
                for i in range(1,8):
                    if (r + dir[0] * i) >= 0 and (r + dir[0] * i) <= 7 and (c + dir[1] * i) >= 0 and (c + dir[1] * i) <= 7:
                        if self.position[r + dir[0] * i][c + dir[1] * i] == '--':
                            moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                        else:
                            if self.position[r + dir[0] * i][c + dir[1] * i][0] == 'b' and self.white_turn:
                                moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                            if self.position[r + dir[0] * i][c + dir[1] * i][0] == 'w' and (not self.white_turn):
                                moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                            break
                    else:
                        break

    # given a knight, generate all possible moves and attend them to the list moves
    def get_knight_moves(self, r, c, moves):
        piece_pinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break
        if not piece_pinned:    
            for i, j in [(1,2), (1,-2), (-1,2), (-1,-2), (2,1), (2,-1), (-2,1), (-2,-1)]:
                if (r + i) >= 0 and (r + i) <= 7 and (c + j) >= 0 and (c + j) <= 7:
                    if self.position[r+i][c+j][0] != 'w' and self.white_turn:
                        moves.append(Move((r, c), (r+i, c+j), self.position))
                    if self.position[r+i][c+j][0] != 'b' and (not self.white_turn):
                        moves.append(Move((r, c), (r+i, c+j), self.position))

    # given a bishop, generate all possible moves and attend them to the list moves
    def get_bishop_moves(self, r, c, moves):
        piece_pinned = False
        pin_dir = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piece_pinned = True
                pin_dir = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        for dir in [(1,1), (1, -1), (-1, 1), (-1, -1)]: # check 4 directions
            if not piece_pinned or pin_dir == dir or pin_dir == (-dir[0], -dir[1]):
                for i in range(1,8):
                    if (r + dir[0] * i) >= 0 and (r + dir[0] * i) <= 7 and (c + dir[1] * i) >= 0 and (c + dir[1] * i) <= 7:
                        if self.position[r + dir[0] * i][c + dir[1] * i] == '--':
                            moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                        else:
                            if self.position[r + dir[0] * i][c + dir[1] * i][0] == 'b' and self.white_turn:
                                moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                            if self.position[r + dir[0] * i][c + dir[1] * i][0] == 'w' and (not self.white_turn):
                                moves.append(Move((r, c), (r + dir[0] * i, c + dir[1] * i), self.position))
                            break
                    else:
                        break

    # given a queen, generate all possible moves and attend them to the list moves
    def get_queen_moves(self, r, c, moves):
        self.get_rook_moves(r, c, moves)
        self.get_bishop_moves(r, c, moves) 

    # given a king, generate all possible moves and attend them to the list moves
    def get_king_moves(self, r, c, moves):
        ally_color = 'w' if self.white_turn else 'b'
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                if i != 0 or j != 0:
                    if (r + i) >= 0 and (r + i) <= 7 and (c + j) >= 0 and (c + j) <= 7:
                        if self.position[r+i][c+j][0] != ally_color:
                            if ally_color == 'w':
                                self.white_king_location = (r+i, c+j)
                            else:
                                self.black_king_location = (r+i, c+j)
                            in_check, checks, pins = self.check_pins_and_checks()
                            if not in_check:
                                moves.append(Move((r, c), (r+i, c+j), self.position))
                            if ally_color == 'w':
                                self.white_king_location = (r, c)
                            else:
                                self.black_king_location = (r, c)
        self.get_castle_moves(r, c, moves, ally_color)

    def get_castle_moves(self, r, c, moves, ally_color):
        if self.in_check:
            return
        if (ally_color == 'w' and self.current_castling_rights.wks) or (ally_color == 'b' and self.current_castling_rights.bks):
            self.get_kingside_castle_moves(r, c, moves, ally_color)
        if (ally_color == 'w' and self.current_castling_rights.wqs) or (ally_color == 'b' and self.current_castling_rights.bqs):
            self.get_queenside_castle_moves(r, c, moves, ally_color)
        
    def get_kingside_castle_moves(self, r, c, moves, ally_color):
        if self.position[r][c+1] == '--' and self.position[r][c+2] == '--':
            if (not self.sq_under_attack(r, c+1)) and (not self.sq_under_attack(r, c+2)):
                moves.append(Move((r, c), (r, c+2), self.position, is_castle = True))

    def get_queenside_castle_moves(self, r, c, moves, ally_color):
        if self.position[r][c-1] == '--' and self.position[r][c-2] == '--' and self.position[r][c-3] == '--':
            if (not self.sq_under_attack(r, c-1)) and (not self.sq_under_attack(r, c-2)):
                moves.append(Move((r, c), (r, c-2), self.position, is_castle = True))

    def check_pins_and_checks(self):
        pins = [] # squares of pinned ally pieces
        checks = [] # squares of checking enemy pieces
        in_check = False
        if self.white_turn:
            ally_color = 'w'
            enemy_color = 'b'
            king_row = self.white_king_location[0]
            king_col = self.white_king_location[1]
        else:
            ally_color = 'b'
            enemy_color = 'w'
            king_row = self.black_king_location[0]
            king_col = self.black_king_location[1]
        directions = [(-1,0), (0,-1), (1,0), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
        for j in range(len(directions)):
            dir = directions[j]
            possible_pin = ()
            for i in range(1,8):
                end_row = king_row + dir[0] * i
                end_col = king_col + dir[1] * i
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    end_piece = self.position[end_row][end_col]
                    if end_piece[0] == ally_color and end_piece[1] != 'K':
                        if possible_pin == ():
                            possible_pin = (end_row, end_col, dir[0], dir[1])
                        else:
                            break
                    elif end_piece[0] == enemy_color:
                        type = end_piece[1]
                        if (0 <= j <= 3 and type == 'R') or \
                            (4 <= j <= 7 and type == 'B') or \
                            (i == 1 and type == 'P' and ((enemy_color == 'w' and 6 <= j <= 7) or (enemy_color == 'b' and 4 <= j <= 5))) or \
                            (type == 'Q') or (i == 1 and type == 'K'):
                            if possible_pin == ():
                                in_check = True
                                checks.append((end_row, end_col, dir[0], dir[1]))
                                break
                            else:
                                pins.append(possible_pin)
                                break
                        else:
                            break
                else:
                    break
        knight_moves = ((1,2), (1,-2), (-1,2), (-1,-2), (2,1), (2,-1), (-2,1), (-2,-1))
        for dir in knight_moves:
            end_row = king_row + dir[0]
            end_col = king_col + dir[1]
            if 0 <= end_row < 8 and 0 <= end_col < 8:
                end_piece = self.position[end_row][end_col]
                if end_piece[0] == enemy_color and end_piece[1] == 'N':
                    in_check = True
                    checks.append((end_row, end_col, dir[0], dir[1]))
        return in_check, checks, pins
    
    def sq_under_attack(self, r, c):
        store_king_location = ()
        if self.white_turn:
            store_king_location = self.white_king_location
            self.white_king_location = (r,c)
        else:
            store_king_location = self.black_king_location
            self.black_king_location = (r,c)
        is_under_attack, temp1, temp2 = self.check_pins_and_checks()
        if self.white_turn:
            self.white_king_location = store_king_location
        else:
            self.black_king_location = store_king_location
        return is_under_attack
    
    def get_array(self):
        cur_array = np.zeros([9, 8, 8])
        for r in range(8): #the first 0:6-th matrices represent the location of pieces
            for c in range(8):
                cur_array[:6, r, c] = str_to_vector[self.position[r][c]]
        cur_array[6,:,:] = np.ones([8,8]) # the 6-th matrix represents the rights to castle
        if not self.castle_rights_log[-1].wks:
            cur_array[6,4:,4:] = np.zeros([4,4])
        if not self.castle_rights_log[-1].bks:
            cur_array[6,:4,4:] = np.zeros([4,4])
        if not self.castle_rights_log[-1].wqs:
            cur_array[6,4:,:4] = np.zeros([4,4]) 
        if not self.castle_rights_log[-1].bqs:
            cur_array[6,:4,:4] = np.zeros([4,4])   
        if len(self.move_history) > 0: #the 7-th matrix represents the last move
            start_row = self.move_history[-1].start_row
            start_col = self.move_history[-1].start_col
            end_row = self.move_history[-1].end_row
            end_col = self.move_history[-1].end_col
            cur_array[7, start_row, start_col] = -1
            cur_array[7, end_row, end_col] = 1
        cur_array[8,:,:] = np.ones([8,8])
        if not self.white_turn: #the 8-th matrix represents the current player
            cur_array[8,:,:] = -1 * cur_array[8,:,:]

        return cur_array
    
    def make_move_by_id(self, move_id):
        start_row, start_col, end_row, end_col, promotionPiece = id_to_move[move_id]
        if promotionPiece != '?':
            if end_row == 0:
                promotionPiece = 'w' + promotionPiece
            elif end_row == 7:
                promotionPiece = 'b' + promotionPiece
        isenpassant = (self.position[start_row][start_col][1] == 'P') and ((end_row, end_col) == self.en_passant_possible_sq)
        iscastle = (self.position[start_row][start_col][1] == 'K') and (abs(end_col - start_col) >= 2)
        move = Move((start_row, start_col), (end_row, end_col), self.position, is_en_passant=isenpassant, is_castle=iscastle, promotion_piece=promotionPiece)

class CastleRights():
    def __init__(self, wks, bks, wqs, bqs):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs
        
# moving one piece and saving the related informations
class Move():
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4,
                     "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {i: j for j, i in ranks_to_rows.items()}
    files_to_cols = {"a": 0, "b": 1, "c": 2, "d": 3,
                     "e": 4, "f": 5, "g": 6, "h": 7}
    cols_to_files = {i: j for j, i in files_to_cols.items()}
    promotion_piece_to_num = {'?': 0, 'Q': 1, 'R': 2, 'B': 3, 'N': 4}
    num_to_promotion_piece = {i: j for j, i in promotion_piece_to_num.items()}

    def __init__(self, start, end, position, is_en_passant = False, is_castle = False, promotion_piece = '?'):
        self.start_row = start[0]
        self.start_col = start[1]
        self.end_row = end[0]
        self.end_col = end[1]
        self.piece_move = position[self.start_row][self.start_col]
        self.piece_caped = position[self.end_row][self.end_col]
        #promotion
        self.is_promotion = (self.piece_move == 'wP' and self.end_row == 0) or (self.piece_move == 'bP' and self.end_row == 7)
        self.promotion_piece = promotion_piece
        #en-passant
        self.is_en_passant = is_en_passant
        if self.is_en_passant:
            self.piece_caped = 'wP' if self.piece_move == 'bP' else 'bP'
        #castle
        self.is_castle = is_castle
    
        #about the chess notation
        self.is_cap = self.piece_caped != '--'
        self.is_check = False
        self.is_checkmate = False
        self.is_stalemate = False
        self.has_rep_pieces = False
        self.has_rep_col = False
        self.has_rep_row = False

    # overriding the equals method
    def __eq__(self, other):
        if isinstance(other, Move):
            return (self.start_row == other.start_row) and (self.start_col == other.start_col) and (self.end_row == other.end_row) and (self.end_col == other.end_col)
        return False

    def get_move_notation(self):
        return self.piece_move[1] + self.get_rank_file(self.start_row, self.start_col) + self.get_rank_file(self.end_row, self.end_col)

    def get_rank_file(self, r, c):
        return self.cols_to_files[c] + self.rows_to_ranks[r]
    
    def check_rep(self, legal_moves):
        for move in legal_moves:
            if move.piece_move == self.piece_move and move.end_row == self.end_row and move.end_col == self.end_col:
                if move.start_row != self.start_row or move.start_col != self.start_col:
                    self.has_rep_pieces = True
                    if move.start_row == self.start_row:
                        self.has_rep_row = True
                    if move.start_col == self.start_col:
                        self.has_rep_col = True

    
    # overriding the str function
    def __str__(self):
        end_sq = self.get_rank_file(self.end_row, self.end_col)
        move_str = ""
        if self.is_castle:
            move_str += "O-O" if self.end_col == 6 else "O-O-O"
        elif self.piece_move[1] == 'P':
            if self.is_cap:
                move_str += (self.cols_to_files[self.start_col] + 'x' + end_sq)
            else:
                move_str += end_sq
            if self.is_promotion:
                move_str += '=' + self.promotion_piece[1]
        else:
            move_str += self.piece_move[1]
            if self.has_rep_pieces:
                if not self.has_rep_col:
                    move_str += self.cols_to_files[self.start_col]
                elif not self.has_rep_row:
                    move_str += self.rows_to_ranks[self.start_row]
                else:
                    move_str += self.get_rank_file(self.start_row, self.start_col)
            if self.is_cap:
                move_str += 'x'
            move_str += end_sq
        if self.is_checkmate:
            move_str += '#'
        elif self.is_stalemate:
            move_str += "1/2-1/2"
        elif self.is_check:
            move_str += '+'    
        return move_str
    
