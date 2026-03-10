FROM python:3.11.9-bookworm

WORKDIR /usr/src/varta

RUN pip install --no-cache-dir prometheus-client==0.23.1 paho-mqtt==2.1.0 requests==2.32.5;

COPY ./varta_pulse.py ./
COPY ./mqtt_pulse.py ./

EXPOSE 8000/tcp

RUN mkdir -p /usr/src/donorgw; \
    touch /usr/src/.insideDocker;

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ENTRYPOINT: zusätzliche Argumente von `docker run` werden an varta_prometheus.py übergeben
ENTRYPOINT [ "python" , "varta_pulse.py"]
