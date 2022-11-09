import uuid
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


class TimeSeries:
    """The time series class"""
    def __init__(
            self,
            metric: str,
            labels: Dict,
            time_stamps: List[int],
            values: List[float]):
        """The time series initializer"""
        self.metric = metric
        self.labels = labels.copy()
        self.time_stamps = time_stamps.copy()
        self.values = values.copy()

        self.__id = f'{metric}_{uuid.uuid4()}'

    @property
    def id(self) -> str:
        """Get the unique id for this time series"""
        return self.__id

    def extend(self, time_stamps: List[int], values: List[float]) -> None:
        """Extends the time series data set by appending time stamps and it's values"""
        if len(time_stamps) != len(values):
            raise ValueError("Extend Error: different length between time_stamps and values!")
        self.time_stamps.extend(time_stamps)
        self.values.extend(values)

    def to_df(self) -> pd.Series:
        """Convert the time series to the pandas DataFrame"""
        timestamp = pd.to_datetime(np.asarray(self.time_stamps).astype(float) * 1000, unit="ms")
        index = pd.to_datetime(timestamp)
        np_values = np.asarray(self.values)

        series = pd.Series(np_values, index=index, name=self.id)
        series = series[~series.index.duplicated()]

        return series