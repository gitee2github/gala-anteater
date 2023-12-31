#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) 2022 Huawei Technologies Co., Ltd.
# gala-anteater is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/

import logging
import os

import numpy as np

from anteater.core.kpi import ModelConfig
from anteater.model.factory import ModelFactory as factory
from anteater.model.process.base import PreProcessor
from anteater.model.process.post_process import PostProcessor
from anteater.utils.constants import POINTS_MINUTE


class OnlineUsadModel:
    """Online Usad model"""

    def __init__(self, config: ModelConfig) -> None:
        """The model initializer"""
        self.config = config
        self.params = config.params

        self.preprocessor = PreProcessor(self.params)
        self.postprocessor = PostProcessor(self.params)

        self.models = {}

    def get_min_predict_minutes(self):
        """Gets minimal minutes for model prediction"""
        return self.params.get('min_predict_minutes')

    def predict(self, x, machine_id):
        """Runs online model predicting"""
        model = self.models.get(machine_id)
        x_test = self.preprocessor.transform(x)
        x_g, x_g_d = model.predict(x_test)
        scores = self.postprocessor.compute_score(x_test, x_g, x_g_d)
        thresholds = self.postprocessor.spot_run(scores)
        y_pred = np.where(scores > thresholds, scores, 0)
        return y_pred

    def train(self, x, machine_id):
        """Runs online model training"""
        sub_directory = os.path.join(self.config.model_path, machine_id)
        model = factory.create_model('usad', sub_directory, **self.params)
        train_df, valid_df = self.preprocessor.split_data(x)
        x_train = self.preprocessor.fit_transform(train_df)
        x_valid = self.preprocessor.transform(valid_df)
        model.train(x_train, x_valid)
        self.models[machine_id] = model
        x_g, x_g_d = model.predict(x_train)
        scores = self.postprocessor.compute_score(x_train, x_g, x_g_d)
        self.postprocessor.fit(scores)

    def is_abnormal(self, y_pred):
        """Checks if existing abnormal or not"""
        if isinstance(y_pred, np.ndarray):
            y_pred = y_pred.tolist()

        if len(y_pred) > POINTS_MINUTE:
            y_pred = y_pred[-POINTS_MINUTE:]

        if len(y_pred) < POINTS_MINUTE:
            logging.warning(
                f'The length of y_pred is less than {POINTS_MINUTE}')
            return False
        th = self.params.get('th')
        abnormal = sum([1 for y in y_pred if y > 0]) >= len(y_pred) * th

        if abnormal:
            logging.info(
                f'Detects abnormal events by {self.__class__.__name__}!')

        return abnormal

    def need_training(self, machine_id):
        """Checks model need to be training before predicting"""
        if machine_id not in self.models:
            return True

        return False
