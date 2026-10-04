import torch 
import torch.nn as nn 

def init_weight(m):
    if isinstance(m, nn.Linear):
        nn.init.kaiming_normal(m.weight, nonlinearity='relu')
        nn.init.zeros_(m.bias)

class ChurnMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(32,1)
        )
        self.apply(init_weight)

def forward(self, x):
    return self.net(x)