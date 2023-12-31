#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) 2023 Huawei Technologies Co., Ltd.
# gala-anteater is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/

import copy
import json
import logging
import os
import stat
from itertools import chain
from os import path
from typing import List, Callable, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from anteater.model.algorithms.early_stop import EarlyStopper
from anteater.utils.ts_dataset import TSDataset


class USADConfig:
    """The USADModel model configuration"""

    filename = "usad_config.json"

    def __init__(self, hidden_sizes: Tuple = (25, 10, 5), latent_size: int = 5,
                 dropout_rate: float = 0.25, batch_size: int = 128,
                 num_epochs: int = 250, lr: float = 0.001, step_size: int = 60,
                 window_size: int = 10, weight_decay: float = 0.01, **kwargs):
        """The usad model config initializer"""
        self.hidden_sizes = hidden_sizes
        self.latent_size = latent_size
        self.dropout_rate = dropout_rate
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.lr = lr
        self.activation = nn.ReLU
        self.step_size = step_size
        self.window_size = window_size
        self.weight_decay = weight_decay

    @classmethod
    def from_dict(cls, config_dict: dict):
        """class initializer from the config dict"""
        config = cls(**config_dict)
        return config

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        """dumps the config dict"""
        config_dict = {}
        for key, val in self.__dict__.items():
            if key == "activation":
                continue
            if hasattr(val, "to_dict"):
                val = val.to_dict()

            config_dict[key] = val

        return config_dict


class USADModel:
    filename = 'usad.pkl'
    config_class = USADConfig

    def __init__(self, config: USADConfig):
        super().__init__()
        self.config = config
        self._num_epochs = config.num_epochs
        self._batch_size = config.batch_size
        self._window_size = config.window_size
        self._lr = config.lr
        self._weight_decay = config.weight_decay

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model: USAD = None

    @classmethod
    def load(cls, folder: str, **kwargs):
        """Loads the model from the file"""
        config_file = os.path.join(folder, cls.config_class.filename)
        state_file = os.path.join(folder, cls.filename)

        if not os.path.isfile(config_file) or not os.path.isfile(state_file):
            logging.warning("Unknown model file, load default vae model!")
            config = USADConfig()
            config.update(**kwargs)
            return USADModel(config)

        modes = stat.S_IWUSR | stat.S_IRUSR
        with os.fdopen(os.open(config_file, os.O_RDONLY, modes), "r") as f:
            config_dict = json.load(f)

        config = cls.config_class.from_dict(config_dict)
        model = cls(config=config)

        state_dict = torch.load(state_file)
        if "config" in state_dict:
            state_dict.pop("config")

        for name, val in state_dict.items():
            if hasattr(model, name):
                setattr(model, name, val)

        return model

    def init_model(self, x_dim):
        """Initializes the model"""
        model = USAD(
            x_dim=x_dim * self._window_size,
            config=self.config
        )

        return model

    def train(self, train_values, valid_values):
        self.model = self.model if self.model else self.init_model(train_values.shape[1])

        train_loader = DataLoader(TSDataset(train_values, self._window_size, self._window_size),
                                  batch_size=self._batch_size,
                                  shuffle=True,
                                  drop_last=True)
        valid_loader = DataLoader(TSDataset(valid_values, self._window_size, self._window_size),
                                  batch_size=self._batch_size)

        early_stopper1 = EarlyStopper(patience=5)
        early_stopper2 = EarlyStopper(patience=5)

        loss_func = nn.MSELoss()

        optimizer_g = torch.optim.Adam(self.model.g_parameters())
        optimizer_d = torch.optim.Adam(self.model.d_parameters())

        for epoch in range(self._num_epochs):
            self.model.train()
            train_g_loss = []
            train_d_loss = []
            for x_batch in train_loader:
                x_batch = x_batch.to(self.device)
                x_batch = torch.flatten(x_batch, start_dim=1)

                w_g, w_d, w_g_d = self.model(x_batch)
                beta = np.divide(1, epoch + 1)
                loss_g = beta * loss_func(x_batch, w_g) + (1 - beta) * loss_func(x_batch, w_g_d)
                loss_d = beta * loss_func(x_batch, w_d) - (1 - beta) * loss_func(x_batch, w_g_d)

                train_g_loss.append(loss_g.detach().numpy())
                train_d_loss.append(loss_d.detach().numpy())

                optimizer_g.zero_grad()
                optimizer_d.zero_grad()

                loss_g.backward(retain_graph=True)
                loss_d.backward()

                optimizer_g.step()
                optimizer_d.step()

            avg_train_g_loss = np.mean(train_g_loss)
            avg_train_d_loss = np.mean(train_d_loss)

            self.model.eval()
            val_g_loss = []
            val_d_loss = []
            for x_val_batch in valid_loader:
                x_val_batch = torch.flatten(x_val_batch, start_dim=1)
                w_g, w_d, w_g_d = self.model(x_val_batch)
                beta = np.divide(1, epoch + 1)
                val_g = beta * loss_func(x_val_batch, w_g) + (1 - beta) * loss_func(x_val_batch, w_g_d)
                val_d = beta * loss_func(x_val_batch, w_d) - (1 - beta) * loss_func(x_val_batch, w_g_d)

                val_g_loss.append(val_g.detach().numpy())
                val_d_loss.append(val_d.detach().numpy())

            avg_val_g_loss = np.mean(val_g_loss)
            avg_val_d_loss = np.mean(val_d_loss)

            logging.info(f'Epoch {epoch}, training loss:\t'
                         f'val_g: {avg_val_g_loss:.3f}\t'
                         f'val_d: {avg_val_d_loss:.3f}\t'
                         f'train_g: {avg_train_g_loss:.3f}\t'
                         f'train_d:{avg_train_d_loss:.3f}')

            if early_stopper1.early_stop(avg_val_g_loss) and \
               early_stopper2.early_stop(avg_val_d_loss):
                logging.info("Early Stopped!")
                break

    def predict(self, values):
        self.model.eval()
        dataset = TSDataset(values, self._window_size, 1)
        x_loader = DataLoader(dataset, batch_size=len(dataset))
        x_pred = next(iter(x_loader))
        x_pred = torch.flatten(x_pred, start_dim=1)
        w_g, _, w_g_d = self.model(x_pred)
        batch_g = torch.reshape(w_g, (-1, self._window_size, values.shape[1])).detach()
        batch_g_d = torch.reshape(w_g_d, (-1, self._window_size, values.shape[1])).detach()
        batch_g = torch.cat([batch_g[0], batch_g[1:, -1]], dim=0).numpy()
        batch_g_d = torch.cat([batch_g_d[0], batch_g_d[1:, -1]], dim=0).numpy()

        return batch_g, batch_g_d

    def save(self, folder):
        """Saves the model into the file"""
        state_dict = {key: copy.deepcopy(val) for key, val in self.__dict__.items()}
        config_dict = self.config.to_dict()

        modes = stat.S_IWUSR | stat.S_IRUSR
        config_file = path.join(folder, self.config_class.filename)
        with os.fdopen(os.open(config_file, os.O_WRONLY | os.O_CREAT, modes), "w") as f:
            f.truncate(0)
            json.dump(config_dict, f, indent=2)

        if "config" in state_dict:
            state_dict.pop("config")

        torch.save(state_dict, os.path.join(folder, self.filename))


class USAD(nn.Module):
    def __init__(self, x_dim, config: USADConfig):
        super().__init__()
        self._shared_encoder = Encoder(x_dim, config)
        self._decoder_g = Decoder(x_dim, config)
        self._decoder_d = Decoder(x_dim, config)

    def g_parameters(self):
        return chain(self._shared_encoder.parameters(), self._decoder_g.parameters())

    def d_parameters(self):
        return chain(self._shared_encoder.parameters(), self._decoder_g.parameters())

    def forward(self, x):
        z = self._shared_encoder(x)
        w_g = self._decoder_g(z)
        w_d = self._decoder_d(z)
        w_g_d = self._decoder_d(self._shared_encoder(w_g))

        return w_g, w_d, w_g_d


class Encoder(nn.Module):
    def __init__(self, x_dim: int, config: USADConfig):
        super().__init__()
        if not config.hidden_sizes:
            hidden_sizes = [x_dim // 2, x_dim // 4]
        else:
            hidden_sizes = config.hidden_sizes

        latent_size = config.latent_size
        dropout_rate = config.dropout_rate
        activation = config.activation

        self.mlp = build_multi_hidden_layers(x_dim, hidden_sizes,
                                             dropout_rate, activation)
        self.linear = nn.Linear(hidden_sizes[-1], latent_size)

    def forward(self, x):
        x = self.mlp(x)
        x = self.linear(x)
        return x


class Decoder(nn.Module):
    def __init__(self, x_dim: int, config: USADConfig):
        super().__init__()
        if not config.hidden_sizes:
            hidden_sizes = [x_dim // 4, x_dim // 2]
        else:
            hidden_sizes = config.hidden_sizes[::-1]

        latent_size = config.latent_size
        dropout_rate = config.dropout_rate
        activation = config.activation

        self.mlp = build_multi_hidden_layers(latent_size, hidden_sizes,
                                             dropout_rate, activation)
        self.output_layer = nn.Linear(hidden_sizes[-1], x_dim)

    def forward(self, x):
        x = self.mlp(x)
        x = self.output_layer(x)
        return x


def build_multi_hidden_layers(input_size: int, hidden_sizes: List[int],
                              dropout_rate: float, activation: Callable):
    """build vae model multi-hidden layers"""
    multi_hidden_layers = []
    for i, _ in enumerate(hidden_sizes):
        in_size = input_size if i == 0 else hidden_sizes[i - 1]
        multi_hidden_layers.append(nn.Linear(in_size, hidden_sizes[i]))
        multi_hidden_layers.append(activation())
        multi_hidden_layers.append(nn.Dropout(dropout_rate))

    return nn.Sequential(*multi_hidden_layers)
