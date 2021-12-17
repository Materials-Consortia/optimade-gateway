FROM python:3.8-alpine

WORKDIR /app

# Copy repo contents
COPY setup.py README.md requirements*.txt ./
COPY optimade_gateway ./optimade_gateway
RUN pip install -e .

EXPOSE 80

ARG CONFIG_FILE=optimade_gateway/config.yml
COPY ${CONFIG_FILE} ./config.yml
ENV OPTIMADE_CONFIG_FILE /app/config.yml

CMD [ "hypercorn", "--bind", "0.0.0.0:80", "optimade_gateway.main:APP" ]
