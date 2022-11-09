import re
from typing import List

from anteater.core.anomaly import Anomaly
from anteater.provider.kafka import KafkaProvider
from anteater.template.template import Template
from anteater.utils.log import logger

PUNCTUATION_PATTERN = re.compile(r"[^\w_\-:.@()+,=;$!*'%]")


class AnomalyReport:
    def __init__(self, provider: KafkaProvider):
        self.provider = provider

    @staticmethod
    def get_entity_id(machine_id, entity_name, labels, keys):
        label_keys = [labels.get(key, '0') for key in keys if key != "machine_id"]
        entity_id = f"{machine_id}_{entity_name}_{'_'.join(label_keys)}"
        entity_id = PUNCTUATION_PATTERN.sub(":", entity_id)

        return entity_id

    def get_keys(self, entity_name):
        keys = self.provider.get_metadata(entity_name)

        if not keys:
            logger.warning(f"Empty metadata for entity name {entity_name}!")

        return keys

    def sent_anomaly(self, anomaly: Anomaly, cause_metrics: List, template: Template):
        keys = self.get_keys(template.entity_name)
        machine_id = template.machine_id
        entity_name = template.entity_name
        labels = anomaly.labels

        template.entity_id = self.get_entity_id(machine_id, entity_name, labels, keys)
        template.keys = keys
        template.description = anomaly.description
        template.cause_metrics = cause_metrics

        msg = template.get_template()
        self.provider.send_message(msg)