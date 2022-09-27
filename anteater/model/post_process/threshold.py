# Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
"""
Time:
Author:
Description: The threhold class for dynamic anomaly score thredhols selection
"""

from collections import deque

import numpy as np
from scipy.signal import savgol_filter

from anteater.model.post_process.base import PostProcess
from anteater.utils.log import Log

log = Log().get_logger()


class Threshold(PostProcess):
    """The threshold post process"""

    def __init__(self, alm_threshold, abs_score=True, quantile: float = None, **kwargs):
        """The threshold post process initializer"""
        self.alm_threshold = alm_threshold
        self.abs_score = abs_score
        self.quantile = quantile

        self._history_scores = deque(maxlen=100000)
        self._latest_alm_threshold = 0
        self._p = 1.2

    def __call__(self, scores):
        """The callable object"""
        self._history_scores.extend(scores[-12:])

        threshold = max(self._latest_alm_threshold, self.alm_threshold)

        updated_scores = np.where(scores >= threshold, scores, 0.0)

        self.update_alm_th(scores)

        return updated_scores

    def update_alm_th(self, scores):
        """Calculates new threshold for alarms"""
        threshold = max(self._latest_alm_threshold, self.alm_threshold)
        self._latest_alm_threshold = (np.average(scores) + threshold) / 2

    def train(self, scores):
        """Train the threshold of post process"""
        if self.abs_score:
            scores = np.abs(scores)

        if self.quantile is not None and self.quantile > 0:
            self.alm_threshold = np.quantile(scores, self.quantile)

    def error_rate(self, look_back):
        """Computes the error rate"""
        hist_scores = np.array(self._history_scores)[-look_back:]

        alarms = hist_scores[np.where(hist_scores >= self.alm_threshold)]

        if len(alarms) and len(hist_scores):
            return len(alarms) / len(hist_scores)

        return 0