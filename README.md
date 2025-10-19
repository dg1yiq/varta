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

## Prometheus

```
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  scrape_protocols:
  - OpenMetricsText1.0.0
  - OpenMetricsText0.0.1
  - PrometheusText1.0.0
  - PrometheusText0.0.4
  evaluation_interval: 15s
  metric_name_validation_scheme: utf8
runtime:
  gogc: 75
alerting:
  alertmanagers:
  - follow_redirects: true
    enable_http2: true
    scheme: http
    timeout: 10s
    api_version: v2
    static_configs:
    - targets: []
scrape_configs:
- job_name: varta
  honor_timestamps: true
  track_timestamps_staleness: false
  scrape_interval: 15s
  scrape_timeout: 10s
  scrape_protocols:
  - OpenMetricsText1.0.0
  - OpenMetricsText0.0.1
  - PrometheusText1.0.0
  - PrometheusText0.0.4
  always_scrape_classic_histograms: false
  convert_classic_histograms_to_nhcb: false
  metrics_path: /metrics
  scheme: http
  enable_compression: true
  metric_name_validation_scheme: utf8
  metric_name_escaping_scheme: allow-utf-8
  follow_redirects: true
  enable_http2: true
  static_configs:
  - targets:
    - host.docker.internal:8000
    labels:
      app: varta
otlp:
  translation_strategy: UnderscoreEscapingWithSuffixes
```

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
docker run -d --restart=always --name=grafana -p 3000:3000 --add-host=host.docker.internal:host-gateway -v grafana-data:/var/lib/grafana grafana/grafana
```

__URL für Prometheus:__ http://http://host.docker.internal:9090
