import random

def get_random_move(legal_moves):
    return legal_moves[random.randint(0, len(legal_moves) - 1)]