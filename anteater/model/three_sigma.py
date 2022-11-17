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


import numpy as np


def three_sigma(values, obs_size, method="abs"):
    """The '3-sigma rule' outlier detect function"""
    if obs_size <= 0:
        raise ValueError("The obs_size should great than zero!")
    if len(values) <= obs_size:
        raise ValueError("The obs_size should be great than values' length")
    train_val = values[:-obs_size]
    obs_val = values[-obs_size:]
    mean = np.mean(train_val)
    std = np.std(train_val)
    if method == "abs":
        outlier = [val for val in obs_val if abs(val - mean) > 3 * std]
    elif method == 'min':
        outlier = [val for val in obs_val if val < mean - 3 * std]
    elif method == 'max':
        outlier = [val for val in obs_val if val > mean + 3 * std]
    else:
        raise ValueError(f'Unknown method {method}')

    return outlier, mean, std