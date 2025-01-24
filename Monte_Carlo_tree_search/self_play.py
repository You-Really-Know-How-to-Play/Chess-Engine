import chess_rule_for_mcts as chess_rule
import numpy as np
import time

def MCT_start_self_play(player, is_shown=False, temp=1e-3):
    gp = chess_rule.GamePosition()
    position_log, mcts_probs, cur_players = [], [], []
    #start self playing
    _count = 0
    while True:
        _count += 1
        if _count % 20 == 0:
            start_time = time.time()
            move, move_probs = player.get_action(gp, temp=temp, return_prob=1)
            print('One move takes:', time.time() - start_time)
        else:
            move, move_probs = player.get_action(gp, temp=temp, return_prob=1)
        #save data
        position_log.append(gp.get_array())
        mcts_probs.append(move_probs)
        cur_is_white = gp.white_turn
        cur_players.append(cur_is_white)
        #make a move
        gp.make_move_by_id(move)
        gp.get_legal_moves()

        #check whether the game ends
        if gp.stalemate or gp.fifty_moves_draw or gp.three_rep_draw:
            end = True
            winner_is_white = None
        elif gp.checkmate:
            end = True
            winner_is_white = True if (not gp.white_turn) else False
        else:
            end = False
            winner_is_white = None

        if end:
            #save win and loss information via the prespective of cur players
            winner_z = np.zeros(len(cur_players))
            if winner_is_white is not None:
                winner_z[np.array(cur_players) == winner_is_white] = 1.0
                winner_z[np.array(cur_players) != winner_is_white] = -1.0
            #reset Monte-Carlo root node
            player.reset_player()
            if is_shown:
                if winner_is_white is not None:
                    winner = "white." if winner_is_white else "black."
                    print("Game ends. Winner is: ", winner)
                else:
                    print('Game ends. Draw.')

            return winner_is_white, zip(position_log, mcts_probs, winner_z)