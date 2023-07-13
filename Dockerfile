# FROM python:3.11.3-slim
# FROM ubuntu:jammy
FROM python:bookworm

RUN \
    echo "**** install runtime dependencies ****" && \
    apt-get update && \
    apt-get install -y \
    git \
    jq \
    libatomic1 \
    nano \
    net-tools \
    wget \
    perl \
    libssl-dev \
    dmidecode \
    zstd \
    binutils \
    xz-utils \
    pciutils \
    gnupg \
    apt-utils\
    ipmitool \
    sshpass

ADD requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
ADD . /app
RUN mkdir -p /app/logs

RUN groupadd --system --gid 1000 appgroup
RUN useradd -u 1000 -d /home/appuser -m -g 1000 appuser
RUN  chown -R appuser /app

# https://linux.dell.com/repo/community/openmanage/
RUN echo "**** install RACADM ****" && \
    echo 'deb http://linux.dell.com/repo/community/openmanage/11000/jammy jammy main' | \
    tee -a /etc/apt/sources.list.d/linux.dell.com.sources.list && \
    wget https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc && \
    apt-key add 0x1285491434D8786F.asc && \
    apt-get update
RUN apt-get install -y srvadmin-hapi || true
COPY  resources/srvadmin-x.postinst /var/lib/dpkg/info/srvadmin-hapi.postinst
RUN echo "**** install RACADM ****" && \
    apt-get install -y srvadmin-hapi
RUN apt-get install -y srvadmin-idracadm7 || true
COPY  resources/srvadmin-x.postinst /var/lib/dpkg/info/srvadmin-idracadm7.postinst
RUN echo "**** install RACADM ****" && \
    apt-get install -y srvadmin-idracadm7
RUN apt-get install -y srvadmin-idracadm8 || true
COPY resources/srvadmin-x.postinst /var/lib/dpkg/info/srvadmin-idracadm8.postinst
RUN echo "**** install RACADM ****" && \
    apt-get install -y srvadmin-idracadm8
# /opt/dell/srvadmin/bin/idracadm7 -r 10.1.7.180 -u root -p pass jobqueue view

USER appuser
CMD python3 main.py