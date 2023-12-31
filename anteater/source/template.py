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

from typing import Dict, List
from anteater.core.anomaly import Anomaly
from anteater.utils.datetime import DateTimeManager as dt


class Template:
    """The anomaly events template"""
    def __init__(self):
        self._timestamp = dt.utc_now()
        self._machine_id = ''
        self._metric = ''
        self._entity_name = ''
        self._score = -1
        self._root_causes = []

        self._labels = {}
        self._entity_id = ""
        self._keywords = []

        self._description = ""
        self._details = {}

        self.header = None
        self.event_type = None

    def get_template(self):
        """Gets the template for app level anomaly events"""
        timestamp = round(self._timestamp.timestamp() * 1000)

        result = {
            'Timestamp': timestamp,
            'Attributes': {
                'entity_id': self._entity_id,
                'event_id': f'{timestamp}_{self._entity_id}',
                'event_type': 'jvm',
                'event_source': 'gala-anteater',
                'keywords': self._keywords
            },
            'Resource': {
                'metric': self._metric,
                'labels': self._labels,
                'score': self._score,
                'root_causes': str(self._root_causes)
            },
            'SeverityText': 'WARN',
            'SeverityNumber': 13,
            'Body': self.get_body()
        }

        return result

    def parse_anomaly(self, anomaly: Anomaly):
        """Parses the anomaly object properties"""
        self._machine_id = anomaly.machine_id
        self._metric = anomaly.metric
        self._entity_name = anomaly.metric
        self._score = anomaly.score
        self._root_causes = anomaly.root_causes

    def add_labels(self, labels):
        """Adds labels property"""
        self._labels = labels

    def add_entity_id(self, entity_id):
        """Adds entity id property"""
        self._entity_id = entity_id

    def add_keywords(self, keywords: List[str]):
        """Adds keywords property"""
        self._keywords = keywords

    def add_description(self, description: str):
        """Add description property"""
        self._description = description

    def add_details(self, details: dict):
        """Adds details property in the body"""
        self._details = details

    def get_body(self) -> str:
        """Gets the template body property"""
        if not self.header:
            raise ValueError('Non-initialized property \'header\' on '
                             f'{self.__class__.__name__}.')
        body = [self._timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                self.header, self._description, self._details]

        return ' - '.join([x for x in body if x])


class AppAnomalyTemplate(Template):
    """The app anomaly template"""

    def __init__(self):
        """The app anomaly template initializer"""
        super().__init__()
        self.header = "Application Failure"
        self.event_type = "app"


class SysAnomalyTemplate(Template):
    """The sys anomaly template"""

    def __init__(self):
        """The sys anomaly template initializer"""
        super().__init__()
        self.header = 'System Failure'
        self.event_type = 'sys'


class JVMAnomalyTemplate(Template):
    """The jvm anomaly template"""

    def __init__(self):
        """The jvm anomaly template initializer"""
        super().__init__()
        self.header = "JVM OutOfMemory"
        self.event_type = 'jvm'
