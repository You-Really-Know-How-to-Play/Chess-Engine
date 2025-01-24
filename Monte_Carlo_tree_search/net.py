import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
from torch.cuda.amp import autocast

#Define residue block
class ResBlock(nn.Module):
    def __init__(self, num_filters = 256):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels=num_filters, out_channels=num_filters, kernel_size=(3, 3), stride=(1, 1), padding=1)
        self.conv1_bn = nn.BatchNorm2d(num_filters)
        self.conv1_act = nn.ReLU()
        self.conv2 = nn.Conv2d(in_channels=num_filters, out_channels=num_filters, kernel_size=(3, 3), stride=(1, 1), padding=1)
        self.conv2_bn = nn.BatchNorm2d(num_filters)
        self.conv2_act = nn.ReLU()

    def forward(self, x):
        y = self.conv1(x)
        y = self.conv1_bn(y)
        y = self.conv1_act(y)
        y = self.conv2(y)
        y = self.conv2_bn(y)
        y = x + y
        return self.conv2_act(y)
    
#Build backbone
class Net(nn.Module):
    def __init__(self, num_channels = 256, num_res_blocks = 7):
        super().__init__()
        #initialize features
        self.conv_block = nn.Conv2d(in_channels=9, out_channels=num_channels, kernel_size=(3, 3), stride=(1, 1), padding=1)
        self.conv_block_bn = nn.BatchNorm2d(num_channels)
        self.conv_block_act = nn.ReLU()
        #extract features by the residue blocks
        self.res_blocks = nn.ModuleList([ResBlock(num_filters=num_channels) for _ in range(num_res_blocks) ])
        #policy head
        self.policy_conv = nn.Conv2d(in_channels=num_channels, out_channels=16, kernel_size=(1, 1), stride=(1, 1))
        self.policy_bn = nn.BatchNorm2d(16)
        self.policy_act = nn.ReLU()
        self.policy_fc = nn.Linear(16 * 8 * 8, 1968) #the nuumber of all possible move ids: 1968
        #value head
        self.value_conv = nn.Conv2d(in_channels=num_channels, out_channels=8, kernel_size=(1,1), stride=(1,1))
        self.value_bn = nn.BatchNorm2d(8)
        self.value_act1 = nn.ReLU()
        self.value_fc1 = nn.Linear(8 * 8 * 8, 256)
        self.value_act2 = nn.ReLU()
        self.value_fc2 = nn.Linear(256, 1)

    #define forward
    def forward(self, x):
        #public head
        x = self.conv_block(x)
        x = self.conv_block_bn(x)
        x = self.conv_block_act(x)
        for layer in self.res_blocks:
            x = layer(x)
        #policy head
        poilcy = self.policy_conv(x)
        poilcy = self.policy_bn(poilcy)
        poilcy = self.policy_act(poilcy)
        poilcy = torch.reshape(poilcy, [-1, 16 * 8 * 8])
        poilcy = self.policy_fc(poilcy)
        poilcy = F.log_softmax(poilcy)
        #value head
        value = self.value_conv(x)
        value = self.value_bn(value)
        value = self.value_act1(value)
        value = torch.reshape(value, [-1, 8 * 8 * 8])
        value = self.value_fc1(value)
        value = self.value_act2(value)
        value = self.value_fc2(value)
        value = F.tanh(value)

        return poilcy, value
    
#policy value net, used for training
class PolicyValueNet:
    def __init__(self, model_file=None, use_gpu=True, device = 'cuda'):
        self.use_gpu=use_gpu
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.l2_const = 2e-3
        self.policy_value_net = Net().to(self.device)
        self.optimizer = torch.optim.Adam(params=self.policy_value_net.parameters(), lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=self.l2_const)
        if model_file:
            self.policy_value_net.load_state_dict(torch.load(model_file))
            
    
    #input a batch of positions, output the proba of moves and evaluation
    def policy_value(self, position_batch):
        self.policy_value_net.eval()
        position_batch = torch.tensor(position_batch).to(self.device)
        log_move_probs, value = self.policy_value_net(position_batch)
        log_move_probs, value = log_move_probs.cpu(), value.cpu()
        move_probs = np.exp(log_move_probs.numpy())
        return move_probs, value.detach().numpy()
    
    #given a game position, return the legal moves and eval
    def policy_value_fn(self, gp):
        self.policy_value_net.eval()
        legal_moves_id_list = gp.get_legal_moves(return_ids = True)
        cur_position = np.ascontiguousarray(gp.get_array().reshape(-1, 9, 8, 8)).astype('float16')
        cur_position = torch.as_tensor(cur_position).to(self.device)
        #predict by nn
        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):
            log_move_probs, value = self.policy_value_net(cur_position)
        log_move_probs, value = log_move_probs.cpu(), value.cpu()
        #move_probs = np.exp(log_move_probs.detach().numpy().astype('float16').flatten())
        move_probs = np.exp(log_move_probs.detach().to(torch.float16).numpy().flatten())
        #only take legal moves
        move_probs = zip(legal_moves_id_list, move_probs[legal_moves_id_list])
        #return move probas, and value
        #return move_probs, value.detach().numpy()
        return move_probs, value.detach().to(torch.float16).numpy()
    
    #save model
    def save_model(self, model_file):
        torch.save(self.policy_value_net.state_dict(), model_file)
    
    def train_step(self, position_batch, mcts_probs, winner_batch, lr = 0.002):
        self.policy_value_net.train()
        position_batch = torch.tensor(position_batch).to(self.device)
        mcts_probs = torch.tensor(mcts_probs).to(self.device)
        winner_batch = torch.tensor(winner_batch).to(self.device)   
        #clear grad
        self.optimizer.zero_grad()     
        #set learning rate
        for param in self.optimizer.param_groups:
            param['lr'] = lr
        #forward
        log_move_probs, value = self.policy_value_net(position_batch)
        value = torch.reshape(value, shape=[-1])
        #value loss
        value_loss = F.mse_loss(input=value, target=winner_batch)
        #policy loss
        policy_loss = -torch.mean(torch.sum(mcts_probs * log_move_probs, dim=1)) 
        #total loss
        loss = value_loss + policy_loss
        #backward
        loss.backward()
        self.optimizer.step()
        #cal entropy
        with torch.no_grad():
            entropy = -torch.mean(
                torch.sum(torch.exp(log_move_probs) * log_move_probs, dim=1)
            )
        return loss.detach().cpu().numpy(), entropy.detach().cpu().numpy()  

if __name__ == '__main__':
    net = Net()
    test_data = torch.ones([8, 9, 8, 8])
    x_act, x_val = net(test_data)
    print(x_act.shape)
    print(x_val.shape)


