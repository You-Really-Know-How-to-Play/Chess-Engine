import numpy as np
from AI_standard_setting import ai_default_setting

def one_move_thinker_find(gp ,legal_moves):
    legal_move_number = len(legal_moves)
    if legal_move_number == 0:
        return
    color_multiplier = 1 if gp.white_turn else -1
    moves_score = np.empty(legal_move_number)
    for i in range(legal_move_number):
        gp.make_move(legal_moves[i])
        opponent_moves = gp.get_legal_moves()
        opponent_move_number = len(opponent_moves)
        if opponent_move_number == 0:
            if gp.checkmate:
                moves_score[i] = color_multiplier * ai_default_setting.WIN
            elif gp.stalemate:
                moves_score[i] = ai_default_setting.DRAW
            gp.undo_move()
            continue
        ai_default_setting.expand_promotions_of_moves(opponent_moves, gp.position)
        opponent_score = np.empty(opponent_move_number)
        for j in range(opponent_move_number):
            gp.make_move(opponent_moves[j])
            opponent_score[j] = ai_default_setting.cal_material_score(gp.position)
            gp.undo_move()
        '''
        if gp.checkmate:
            moves_score[i] = color_multiplier * ai_default_setting.WIN
        elif gp.stalemate:
            moves_score[i] = ai_default_setting.DRAW
        else:
            moves_score[i] = ai_default_setting.cal_material_score(gp.position)
        '''
        gp.undo_move()
        moves_score[i] = np.amin(opponent_score) if gp.white_turn else np.amax(opponent_score)
    if gp.white_turn:
        best_score = np.amax(moves_score)
    else:
        best_score = np.amin(moves_score)
    best_moves = np.where(moves_score == best_score)[0]
    choice = np.random.randint(0, len(best_moves))
    return legal_moves[best_moves[choice]]

    

