Copyright (C) 2021, DG1YIQ

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS.  IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.

## What is this?

This is a simple Programm to connect Varte Storage to Prometheus and Grafana.

## Prometheus

__Attention:__ You need to adjust the `prometheus.yml` configuration file in the `./prometheus` folder to point to the Varta Storage Exporter!

prometheus.yml (Section to add/check/modify):
```
...
  
  static_configs:
  - targets:
    - host.docker.internal:8000
    labels:
      app: varta
  
...
```

Docker Run Command:

```
docker volume create prometheus-data
docker run -d \
           --restart=always \
           --name prometheus \
           -p 9090:9090 \
           --add-host=host.docker.internal:host-gateway \
           -v prometheus-data:/prometheus \
           -v ./prometheus:/etc/prometheus \
           prom/prometheus
```

## Grafana

```
docker volume create grafana-data
docker run -d \
           --restart=always \
           --name=grafana \
           -p 3000:3000 \
           --add-host=host.docker.internal:host-gateway \
           -v grafana-data:/var/lib/grafana \
           grafana/grafana
```

__URL für Prometheus Database:__ http://host.docker.internal:9090

## Varta Storage Exporter

```
docker build -t varta-exporter .
docker run -d \
           --restart=always \
           --name=varta-exporter \
           -p 8000:8000 \
           --add-host=host.docker.internal:host-gateway \
           varta-exporter 192.168.3.30
```

## Alternativ Docker Compose:

```
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: always
    ports:
      - "9090:9090"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - prometheus-data:/prometheus
      - ./prometheus:/etc/prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: always
    ports:
      - "3000:3000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - grafana-data:/var/lib/grafana

  varta-exporter:
    build:
      context: .
      dockerfile: Dockerfile
    image: varta-exporter:latest
    container_name: varta-exporter
    restart: always
    ports:
      - "8000:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    command: ["192.168.3.30"]

volumes:
  prometheus-data:
  grafana-data:
```