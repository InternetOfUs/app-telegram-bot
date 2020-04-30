FROM registry.u-hopper.com:5000/uhopper/chatbot-core:1.3.0

LABEL authors="Carlo Caprini, Stefano Tavonatti"

COPY requirements.txt .
COPY requirements-common.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-common.txt

COPY run.sh .

ADD src/ /scripts/

WORKDIR /scripts

ADD test/ test/

ENV PYTHONPATH /scripts
