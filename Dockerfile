FROM python:3.10-alpine

WORKDIR /app

# Copy repo contents
COPY pyproject.toml README.md ./
COPY optimade_gateway ./optimade_gateway
COPY .ci ./.ci
RUN pip install -e .

ENV PORT=80
EXPOSE ${PORT}

ARG CONFIG_FILE=optimade_gateway/config.json
COPY ${CONFIG_FILE} ./config.json
ENV OPTIMADE_CONFIG_FILE /app/config.json

CMD uvicorn --host=0.0.0.0 --port=${PORT} optimade_gateway.main:APP
