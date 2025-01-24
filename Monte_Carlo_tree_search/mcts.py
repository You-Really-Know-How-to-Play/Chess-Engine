import numpy as np
import copy
from config import CONFIG

def softmax(x):
    probs = np.exp(x - np.max(x))
    probs /= np.sum(probs)
    return probs

#define tree node
class TreeNode(object):
    def __init__(self, parent, prior_p):
        self._parent = parent
        self._children = {}    #map from move to TreeNode
        self._n_visits = 0      #visiting times of the node
        self._Q = 0             #value of the move corresponding to the node
        self.u = 0             #confidence upper bound    (PUCT)
        self._P = prior_p

    def expand(self, action_priors): #set the probs of illegal moves as 0
        #set new nodes
        for action, prob in action_priors:
            if action not in self._children:
                self._children[action] =  TreeNode(self, prob)

    def select(self, c_puct):
        #select the node that provides the maximum of Q+U
        return max(self._children.items(), key = lambda act_node: act_node[1].get_value(c_puct))
    
    def get_value(self, c_puct):
        #calculate and return the value of the node
        #c_puct: (0, inf)
        self._u = (c_puct * self._P *np.sqrt(self._parent._n_visits) / (1 + self._n_visits))
        return self._Q + self._u
    
    def update(self, leaf_value):
        #update backward
        self._n_visits += 1
        #update Q
        self._Q += 1.0 * (leaf_value - self._Q) / self._n_visits

    def update_recursive(self, leaf_value):
        #update all direct nodes
        #if the node is not the root, update its parent first
        if self._parent:
            self._parent.update_recursive(-leaf_value) #change the perspective of player
        self.update(leaf_value)

    def is_leaf(self):
        return self._children == {}

    def is_root(self):
        return self._parent is None

class MonteCarloTreeSearch(object):
    def __init__(self, policy_value_fn, c_puct=5, n_playout=2000):
        #recieve the position, output the move probs and eval
        self._root = TreeNode(None, 1.0)
        self._policy = policy_value_fn
        self._c_puct = c_puct
        self._n_playout = n_playout

    def _playout(self, gp):
        #do a search, update the params of the treenodes by the eval of leafnodes
        #note that the game position is changed
        node = self._root
        while True:
            if node.is_leaf():
                break
            action, node = node.select(self._c_puct)
            gp.make_move_by_id(action)

        #use net to eval nodes, the net should output the list of (action, prob) and the score of current player [-1, 1]
        action_probs, leaf_value = self._policy(gp)
        
        #check whether the game ends
        if gp.stalemate or gp.fifty_moves_draw or gp.three_rep_draw:
            end = True
            winner = None
        elif gp.checkmate:
            end = True
            winner = 1 if (not gp.white_turn) else -1
        else:
            end = False
            winner = None

        if not end:
            node.expand(action_probs)
        else:
            #if ends, subtitude the values of treenodes by 1 or 0
            if winner is None:    #Draw
                leaf_value = 0.0
            else:   #the current player must win, one cannot lose immediately by making a move
                leaf_value = 1.0
        
        #update nodes and visiting times
        #the negetive sign should be added since the two players use a same tree
        node.update_recursive(-leaf_value)

    def get_move_probs(self, gp, temp=1e-3):
        #do all search in order, and return vaild moves and corresponding probs
        #temp: tempreture, in (0, 1]

        for n in range(self._n_playout):
            gp_copy = copy.deepcopy(gp)
            self._playout(gp_copy)

        #calculate the moving prob using the visiting times of the root node
        act_visits= [(act, node._n_visits)
                     for act, node in self._root._children.items()]
        acts, visits = zip(*act_visits)
        act_probs = softmax(1.0 / temp * np.log(np.array(visits) + 1e-10))
        return acts, act_probs    

    def update_with_move(self, last_move):
        #update in the current tree, keep everything we know about the tree
        if last_move in self._root._children:
            self._root = self._root._children[last_move]
            self._root._parent = None
        else:
            self._root = TreeNode(None, 1.0)

    def __str__(self):
        return 'MCTS'    
    
#AI player based on MCTS
class MCTSPlayer(object):
    def __init__(self, policy_value_function, c_puct=5, n_playout=2000, is_selfplay=0):
        self.mcts = MonteCarloTreeSearch(policy_value_function, c_puct, n_playout)
        self._is_selfplay = is_selfplay
        self.agent = "AI"

    def set_player_ind(self, p):
        self.player = p

    #reset the searching tree
    def reset_player(self):
        self.mcts.update_with_move(-1)

    def __str__(self):
        return 'MCTS {}'.format(self.player)

    #get action
    def get_action(self, gp, temp=1e-3, return_prob=0):
        #return the pi vector from MCTS algorism, just like the alphaGO_Zero paper
        move_probs = np.zeros(1968)

        acts, probs = self.mcts.get_move_probs(gp, temp)
        move_probs[list(acts)] = probs
        if self._is_selfplay:
            #adding Diriclet noise for self playing
            move = np.random.choice(
                acts,
                p=0.75*probs + 0.25*np.random.dirichlet(CONFIG['dirichlet'] * np.ones(len(probs)))
            )
            #refresh the root node, and reuse searching tree
            self.mcts.update_with_move(move)
        else:
            move = np.random.choice(acts, p=probs)
            #refresh the root node
            self.mcts.update_with_move(-1)
        if return_prob:
            return move, move_probs
        else:
            return move