# syntax=docker/dockerfile:1

# Copyright (c) 2022 Huawei Technologies Co., Ltd.
# A-Ops is licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# Create: 2022-06-01

#
# Dockerfile for building openEuler aops gala-anteater docker image.
#
# Usage:
#       docker build -f Dockerfile -t gala-anteater:1.0.0 .
#       docker run --env kafka_server={localhost} --env kafka_port={port} --env prometheus_server={localhost} \
#                  --env prometheus_port={port} -it gala-anteater:1.0.0
#

# base image
FROM python:3.7-slim-buster

# Define variables.
ENV kafka_server "localhost"
ENV kafka_port "9092"
ENV prometheus_server "localhost"
ENV prometheus_port "9090"

ENV PYTHONPATH "${PYTHONPATH}:/gala-anteather/anteater"

WORKDIR /home/gala-anteather

COPY requirements.txt requirements.txt
COPY . /home/gala-anteather
COPY anteater/config /etc/gala-anteater/config

# Setting the pip3 source
# RUN pip3 config set global.index-url http://cmc-cd-mirror.rnd.huawei.com/pypi/simple/ \
#   &&  pip3 config set global.trusted-host cmc-cd-mirror.rnd.huawei.com

RUN pip3 install --no-cache-dir -r requirements.txt

CMD python3 ./anteater/main.py --kafka_server ${kafka_server} --kafka_port ${kafka_port} \
    --prometheus_server ${prometheus_server} --prometheus_port ${prometheus_port}