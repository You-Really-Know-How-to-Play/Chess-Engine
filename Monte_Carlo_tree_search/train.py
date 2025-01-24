import random
from collections import deque

import numpy as np
import pickle
import time

from config import CONFIG
import chess_rule_for_mcts as chess_rule
from mcts import MCTSPlayer
from net import PolicyValueNet

#define the training process
class TrainPipeline:
    def __init__(self, init_model=None):
        #train params
        self.gp = chess_rule.GamePosition()
        self.n_playout = CONFIG['play_out']
        self.c_puct = CONFIG['c_puct']
        self.learn_rate = 1e-3
        self.lr_multiplier = 1
        self.temp = 1.0
        self.batch_size = CONFIG['batch_size'] 
        self.epochs = CONFIG['epochs']  
        self.kl_targ = CONFIG['kl_targ'] 
        self.check_freq = 100  #save model freq
        self.game_batch_num = CONFIG['game_batch_num'] 
        self.best_win_ratio = 0.0
        self.pure_mcts_playout_num = 500
        self.buffer_size = maxlen=CONFIG['buffer_size']
        self.data_buffer = deque(maxlen=self.buffer_size)
        if init_model:
            try:
                self.policy_value_net = PolicyValueNet(model_file=init_model)
                print('Loaded the latest model.')
            except:
                print('Model path not exists, training from origin.')
                self.policy_value_net = PolicyValueNet()
        else:
            print('Training from origin.')
            self.policy_value_net = PolicyValueNet()

    def policy_updata(self):
        mini_batch = random.sample(self.data_buffer, self.batch_size)
        # print(mini_batch[0][1],mini_batch[1][1])
        state_batch = [data[0] for data in mini_batch]
        state_batch = np.array(state_batch).astype('float32')

        mcts_probs_batch = [data[1] for data in mini_batch]
        mcts_probs_batch = np.array(mcts_probs_batch).astype('float32')

        winner_batch = [data[2] for data in mini_batch]
        winner_batch = np.array(winner_batch).astype('float32')

        #old policy and value
        old_probs, old_v = self.policy_value_net.policy_value(state_batch)

        for i in range(self.epochs):
            loss, entropy = self.policy_value_net.train_step(
                state_batch,
                mcts_probs_batch,
                winner_batch,
                self.learn_rate * self.lr_multiplier
            )
            #new policy and value
            new_probs, new_v = self.policy_value_net.policy_value(state_batch)

            kl = np.mean(np.sum(old_probs * (
                np.log(old_probs + 1e-10) - np.log(new_probs + 1e-10)),
                                axis=1))
            if kl > self.kl_targ * 4: 
                break

        #adjusting lr
        if kl > self.kl_targ * 2 and self.lr_multiplier > 0.1:
            self.lr_multiplier /= 1.5
        elif kl < self.kl_targ / 2 and self.lr_multiplier < 10:
            self.lr_multiplier *= 1.5
        # print(old_v.flatten(),new_v.flatten())
        explained_var_old = (1 -
                             np.var(np.array(winner_batch) - old_v.flatten()) /
                             np.var(np.array(winner_batch)))
        explained_var_new = (1 -
                             np.var(np.array(winner_batch) - new_v.flatten()) /
                             np.var(np.array(winner_batch)))

        print(("kl:{:.5f},"
               "lr_multiplier:{:.3f},"
               "loss:{},"
               "entropy:{},"
               "explained_var_old:{:.9f},"
               "explained_var_new:{:.9f}"
               ).format(kl,
                        self.lr_multiplier,
                        loss,
                        entropy,
                        explained_var_old,
                        explained_var_new))
        return loss, entropy
    
    def run(self):
        #start training
        try:
            for i in range(self.game_batch_num):
                while True:
                    try:
                        with open(CONFIG['train_data_buffer_path'], 'rb') as data_dict:
                            data_file = pickle.load(data_dict)
                            self.data_buffer = data_file['data_buffer']
                            self.iters = data_file['iters']
                            del data_file
                        print('已载入数据')
                        break
                    except:
                        time.sleep(30)
                print('step i {}: '.format(self.iters))
                if len(self.data_buffer) > self.batch_size:
                    loss, entropy = self.policy_updata()
                    #save model
                    self.policy_value_net.save_model(CONFIG['pytorch_model_path'])


                time.sleep(CONFIG['train_update_interval'])  #update the model for every 10 min

                if (i + 1) % self.check_freq == 0:
                    print("current self-play batch: {}".format(i + 1))
                    self.policy_value_net.save_model('models/current_policy_batch{}.model'.format(i + 1))
        except KeyboardInterrupt:
            print('\n\rquit')    


training_pipeline = TrainPipeline(init_model='current_policy.pkl')
training_pipeline.run()
