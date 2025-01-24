import random
from AI_standard_setting import ai_default_setting

def minimax_find_move(gp, legal_moves):
    global next_move
    next_move = None
    minimax_step(gp, legal_moves, ai_default_setting.DEPTH, gp.white_turn)
    return next_move

def minimax_step(gp, legal_moves, depth, white_turn):
    global next_move
    if depth == 0 or len(legal_moves) == 0:
        return ai_default_setting.evaluate_position(gp, legal_moves)
    
    random.shuffle(legal_moves)
    color_multiplier = 1 if white_turn else -1
    max_eval = -color_multiplier * (ai_default_setting.WIN + 1)
    for move in legal_moves:
        gp.make_move(move)
        next_moves = gp.get_legal_moves()
        ai_default_setting.expand_promotions_of_moves(next_moves, gp.position)
        cur_eval = minimax_step(gp, next_moves, depth - 1, gp.white_turn)
        if color_multiplier * cur_eval > color_multiplier * max_eval:
            max_eval = cur_eval
            if depth == ai_default_setting.DEPTH:
                next_move = move
        gp.undo_move()
    return max_eval

def Nega_max_find_move(gp, legal_moves):
    global next_move
    next_move = None
    random.shuffle(legal_moves)
    Nega_max_alpha_beta_pruning_step(gp, legal_moves, ai_default_setting.DEPTH, -(ai_default_setting.WIN + 1), (ai_default_setting.WIN + 1), 1 if gp.white_turn else -1)
    return next_move

def Nega_max_step(gp, legal_moves, depth, color_multiplier):
    global next_move
    if depth == 0 or len(legal_moves) == 0:
        return color_multiplier * ai_default_setting.evaluate_position(gp, legal_moves)   
    
    max_eval = -(ai_default_setting.WIN + 1)
    for move in legal_moves:
        gp.make_move(move)
        next_moves = gp.get_legal_moves()
        ai_default_setting.expand_promotions_of_moves(next_moves, gp.position)
        cur_eval = -Nega_max_step(gp, next_moves, depth -1, -color_multiplier)
        if cur_eval > max_eval:
            max_eval = cur_eval
            if depth == ai_default_setting.DEPTH:
                next_move = move
        gp.undo_move()
    return max_eval

#pruning when we reach a good enough eval alpha, or bad enough eval beta
def Nega_max_alpha_beta_pruning_step(gp, legal_moves, depth, alpha, beta, color_multiplier):
    global next_move
    if depth == 0 or len(legal_moves) == 0:
        return color_multiplier * ai_default_setting.evaluate_position(gp, legal_moves)   
    
    #move ordering(to be done)
    
    max_eval = -(ai_default_setting.WIN + 1)
    for move in legal_moves:
        gp.make_move(move)
        next_moves = gp.get_legal_moves()
        ai_default_setting.expand_promotions_of_moves(next_moves, gp.position)
        cur_eval = -Nega_max_alpha_beta_pruning_step(gp, next_moves, depth - 1, -beta, -alpha, -color_multiplier)
        if cur_eval > max_eval:
            max_eval = cur_eval
            if depth == ai_default_setting.DEPTH:
                next_move = move
        gp.undo_move()
        if max_eval > alpha: #pruning
            alpha = max_eval
        if alpha >= beta:
            break
    return max_eval

    