FROM python:bookworm

RUN \
    echo "**** install runtime dependencies ****" && \
    apt-get update && \
    apt-get install -y \
    ipmitool \
    sshpass

ADD requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
ADD . /app
RUN mkdir -p /app/logs

RUN chmod 777 /app/resources/docker-entrypoint.sh

ENTRYPOINT ["/app/resources/docker-entrypoint.sh"]