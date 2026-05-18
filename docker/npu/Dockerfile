FROM hub.szaic.com/sjtu-base/sjtu_base-pytorch-for-ascend:cann8.2rc1-torch2.6.0-py3.10

SHELL ["/bin/bash", "-c"]

RUN sed -i -r 's@(archive|security|ports).ubuntu.com@mirrors.aliyun.com@g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends git vim wget curl sudo tmux \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN git config --global http.version HTTP/1.1 \
    && git clone --depth 1 --branch v0.9.3 https://github.com/hiyouga/LLaMA-Factory.git /opt/LLaMA-Factory \
    && cd /opt/LLaMA-Factory \
    && pip install --no-cache-dir --no-deps -e .

WORKDIR /workspace
