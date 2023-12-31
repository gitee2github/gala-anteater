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
"""
Time: 2023-6-12
Author: Zhenxing
Description: The normalization method for the data processing
"""

import os

import joblib
from sklearn.preprocessing import MinMaxScaler

from anteater.utils.log import logger


class Normalization:
    """The normalization class for the data processing"""

    filename = "normalization.pkl"

    def __init__(self, **kwargs):
        """The normalizer initializer"""
        self.normalizer = MinMaxScaler(**kwargs)

    @classmethod
    def load(cls, folder, **kwargs):
        """Loads model from the file"""
        file = os.path.join(folder, cls.filename)

        if not os.path.isfile(file):
            logger.warning("Unknown model file, load default norm model!")
            return Normalization(**kwargs)

        model = cls(**kwargs)
        model.normalizer = joblib.load(file)
        return model

    def save(self, folder):
        """Saves the model into the file"""
        model_path = os.path.join(folder, self.filename)
        joblib.dump(self.normalizer, model_path)

    def fit_transform(self, x):
        """Fits and transforms the data"""
        x_norm = self.normalizer.fit_transform(x)
        return x_norm

    def transform(self, x):
        """Transform the data"""
        x_norm = self.normalizer.transform(x)
        return x_norm
