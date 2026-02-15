FROM debian:bookworm

RUN set -ex; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get -qq update; \
    apt-get -y install \
      ca-certificates \
      wget \
      unzip \
      mosquitto; \
      apt-get -y --purge autoremove; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*;

RUN rm -rf /etc/localtime; \
    ln -s /usr/share/zoneinfo/Europe/Berlin /etc/localtime;

RUN mkdir -p /var/run/mosquitto; \
    touch /var/log/mosquitto/mosquitto.log; \
    chown -R mosquitto:mosquitto /var/run/mosquitto /var/log/mosquitto;

RUN echo "listener 1883 0.0.0.0" | tee -a /etc/mosquitto/mosquitto.conf; \
    echo "listener 9001 0.0.0.0" | tee -a /etc/mosquitto/mosquitto.conf; \
    echo "protocol websockets" | tee -a /etc/mosquitto/mosquitto.conf; \
    echo "allow_anonymous true" | tee -a /etc/mosquitto/mosquitto.conf;

EXPOSE 1883/tcp
EXPOSE 9001/tcp

USER mosquitto:mosquitto

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]

