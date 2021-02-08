FROM python:3.8-alpine

WORKDIR /app

# Copy repo contents
COPY setup.py README.md requirements*.txt ./
COPY optimade_gateway optimade_gateway
COPY tests/static/test_gateways.json .ci/
RUN apk add git \
    && pip install git+https://github.com/Materials-Consortia/optimade-python-tools.git@master#egg=optimade \
    && pip install -e .

EXPOSE 80

CMD [ "uvicorn", "--host", "0.0.0.0", "--port", "80", "--loop", "asyncio", "optimade_gateway.main:APP" ]
