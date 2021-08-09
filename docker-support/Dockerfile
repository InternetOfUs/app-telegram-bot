FROM public.registry.u-hopper.com/python:3.8 as builder

ARG PIP_CONF_DOCKER

RUN mkdir -p /root/.config/pip
RUN echo "${PIP_CONF_DOCKER}" > /root/.config/pip/pip.conf
ENV PIP_CONFIG_FILE /root/.config/pip/pip.conf





RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY wenet-common-models-requirements.txt .
RUN pip install --user --no-cache-dir -r wenet-common-models-requirements.txt
COPY chatbot-core-requirements.txt .
RUN pip install --user --no-cache-dir -r chatbot-core-requirements.txt
COPY utils-requirements.txt .
RUN pip install --user --no-cache-dir -r utils-requirements.txt

FROM public.registry.u-hopper.com/python:3.8

COPY --from=builder /root/.local /root/.local

RUN pip install coverage pytest-cov anybadge PyYAML

ENV PATH=/root/.local/bin:$PATH

WORKDIR /scripts

COPY run.sh .

COPY run_ws.sh .
COPY run_eat-together-bot.sh .
COPY run_ask-for-help-bot.sh .

ADD src/ /scripts/
ADD documentation/ /documentation/

ENV DOCUMENTATION_PATH /documentation

ADD test/ /scripts/test/
COPY run_tests.sh .
COPY test.sh .

COPY run_test_coverage.sh .
COPY .coveragerc .


ADD translations translations


ENV PYTHONPATH /scripts

ARG GIT_REF

# Specific runners for each defined service need to be called explicitly
