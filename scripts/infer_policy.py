#!/usr/bin/env python3
import numpy as np
import torch
from train_model import ConvPolicy, one_hot_grid


def load_model(path='models/conv_policy.pt', device='cpu'):
    m = ConvPolicy().to(device)
    m.load_state_dict(torch.load(path, map_location=device))
    m.eval()
    return m


def predict_next_direction(model, maze, current, goal, device='cpu'):
    grid = one_hot_grid(maze, current, goal)
    x = torch.tensor(grid, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        pred = logits.argmax(dim=1).item()
    return pred  # 0:up,1:down,2:left,3:right


if __name__ == '__main__':
    print('Use this as a library from the game or tests.')
