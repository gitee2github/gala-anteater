#!/usr/bin/python3
# ******************************************************************************
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
Description: Some common functions are able to use in this project.
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple

from anteater.service.kafka import KafkaConsumer, KafkaProducer, EntityVariable
from anteater.service.prometheus import Prometheus
from anteater.utils.settings import ServiceSettings, MetricSettings, ModelSettings
from anteater.utils.log import Log

log = Log().get_logger()

PUNCTUATION_PATTERN = re.compile(r"[^\w_\-:.@()+,=;$!*'%]")


def get_file_path(file_name):
    """Gets root path of anteater"""
    root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    file_path = os.path.join(root_path, "file" + os.sep + file_name)

    return file_path


def load_prometheus_client() -> Prometheus:
    """Load and initialize the prometheus client"""
    settings = ServiceSettings()
    server = settings.prometheus_server
    port = settings.prometheus_port

    client = Prometheus(server, port)

    return client


def update_entity_variable() -> KafkaConsumer:
    """Updates entity variables by querying data from Kafka under sub thread"""
    log.info("Start to try updating global configurations by querying data from Kafka!")

    service_settings = ServiceSettings()
    server = service_settings.kafka_server
    port = service_settings.kafka_port
    topic = service_settings.kafka_consumer_topic

    metric_settings = MetricSettings()
    entity_name = metric_settings.entity_name

    consumer = KafkaConsumer(server, port, topic, entity_name)
    consumer.start()

    return consumer


def update_service_settings(parser: Dict[str, Any]) -> None:
    """Update service settings globally"""
    settings = ServiceSettings()
    settings.kafka_server = parser["kafka_server"]
    settings.kafka_port = parser["kafka_port"]
    settings.prometheus_server = parser["prometheus_server"]
    settings.prometheus_port = parser["prometheus_port"]


def update_model_settings(parser: Dict[str, Any]) -> None:
    """Updates model settings globally"""
    settings = ModelSettings()
    settings.hybrid_model_th = parser["threshold"]


def get_kafka_message(utc_now: datetime, y_pred: List, machine_id: str, key_anomalies: Tuple[str, Dict, float],
                      rec_anomalies: List[Tuple[str, Dict, float]]) -> Dict[str, Any]:
    """Generates the Kafka message based the parameters"""
    variable = EntityVariable.variable.copy()

    entity_name = variable["entity_name"]
    filtered_metric_label = {}
    keys = []

    metric_label = key_anomalies[1]
    metric_id = key_anomalies[0]

    for key in variable["keys"]:
        filtered_metric_label[key] = metric_label[key]
        if key != "machine_id":
            keys.append(metric_label[key])

    entity_id = f"{machine_id}_{entity_name}_{'_'.join(keys)}"
    entity_id = PUNCTUATION_PATTERN.sub(":", entity_id)

    sample_count = len(y_pred)
    if sample_count != 0:
        anomaly_score = sum(y_pred) / sample_count
    else:
        anomaly_score = 0

    recommend_metrics = dict()
    for name, label, score in rec_anomalies:
        recommend_metrics[name] = {"label": label, "score": score}

    timestamp = round(utc_now.timestamp() * 1000)

    message = {
        "Timestamp": timestamp,
        "Attributes": {
            "entity_id": entity_id,
            "event_id": f"{timestamp}_{entity_id}",
            "event_type": "app"
        },
        "Resource": {
            "anomaly_score": anomaly_score,
            "anomaly_count": sum(y_pred),
            "total_count": len(y_pred),
            "duration": 60,
            "anomaly_ratio": anomaly_score,
            "metric_label": filtered_metric_label,
            "recommend_metrics": recommend_metrics,
            "metrics": metric_id,
        },
        "SeverityText": "WARN",
        "SeverityNumber": 13,
        "Body": f"{utc_now.strftime('%c')}, WARN, APP may be impacting sli performance issues.",
        "event_id": f"{timestamp}_{entity_id}"
    }

    return message


def sent_to_kafka(message: Dict[str, Any]) -> None:
    """Sent message to kafka"""
    settings = ServiceSettings()

    server = settings.kafka_server
    port = settings.kafka_port
    topic = settings.kafka_procedure_topic

    kafka_producer = KafkaProducer(server, port)
    kafka_producer.send_message(topic, message)
