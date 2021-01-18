FROM public.registry.u-hopper.com/python:3.8





RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wenet-common-models-requirements.txt .
RUN pip install --no-cache-dir -r wenet-common-models-requirements.txt
COPY chatbot-core-requirements.txt .
RUN pip install --no-cache-dir -r chatbot-core-requirements.txt
COPY utils-requirements.txt .
RUN pip install --no-cache-dir -r utils-requirements.txt

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



ENV PYTHONPATH /scripts

# Specific runners for each defined service need to be called explicitly
