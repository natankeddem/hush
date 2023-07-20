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

RUN chmod 777 /app/resources/docker-entrypoint.sh

# https://linux.dell.com/repo/community/openmanage/
RUN echo "**** install RACADM ****" && \
    echo "deb http://linux.dell.com/repo/community/openmanage/11000/jammy jammy main" | \
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

ENTRYPOINT ["/app/resources/docker-entrypoint.sh"]