import torch
from torch import nn
from torch import optim
from torch.nn import functional
from torch import autograd
from aiohttp import web

from utils import EpochProgress
from manager import Manager
from worker import ExperimentWorker

import random


class Model(nn.Module):
    name = "lineartest"

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(28*28, 100)
        self.fc2 = nn.Linear(100, 100)
        self.fc3 = nn.Linear(100, 10)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, X):
        X = functional.tanh(self.fc1(X))
        X = functional.tanh(self.fc2(X))
        X = self.softmax(self.fc3(X))
        return X

    def __hash__(self):
        return hash(tuple((k, *v.shape) for k, v in self.state_dict().items()))

    def train(self, X, y, n_epoch=32, lr=0.001, batch_size=32, verbose=True):
        X = autograd.Variable(X)
        y = autograd.Variable(y)
        loss = nn.CrossEntropyLoss()
        idxs = torch.randperm(X.shape[0])
        optimizer = optim.SGD(self.parameters(), lr=lr)
        loss_history = []
        for epoch in range(n_epoch):
            batch_iter = EpochProgress(epoch, torch.split(idxs, batch_size),
                                       verbose=verbose)
            for batch_idxs in batch_iter:
                optimizer.zero_grad()
                X_batch = X[batch_idxs]
                y_batch = y[batch_idxs]
                output = self(X_batch)
                loss_batch = loss(output, y_batch)
                batch_iter.update_loss(loss_batch)
                loss_batch.backward()
                optimizer.step()
            loss_history.append(batch_iter.loss)
        return loss_history


class LinearTestWorker(ExperimentWorker):
    def get_data(self):
        n = random.randint(5, 20)
        X = torch.randn(32*n, 28*28)
        _, y = torch.randn(32*n, 10).max(1)
        return (X, y), n*32


if __name__ == "__main__":
    import sys
    role = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])
    app = web.Application()

    if role == 'manager':
        app = web.Application()
        manager = Manager(app)
        model = Model()
        manager.register_experiment(model)
    elif role == 'worker':
        model = Model()
        worker = LinearTestWorker(app, model, host, port=port)
    web.run_app(app, port=port)
