Copyright (C) 2025, DG1YIQ

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

This is a simple Programm to connect Varte Storage to Prometheus with Grafana and also export important Metrics via MQTT to use in Home Assistant with auto Discovery.

## Grafana

__URL for Prometheus Database:__ http://host.docker.internal:9090

## Home Assistant

__URL for MQTT Broker:__ host.docker.internal:1883

## Konfiguration des Varta Exporters:

Bitte in der Docker Compose bitte die Startparameter des Varta Exporters anpassen, damit die Verbindung zum Varta Storage hergestellt werden kann. Durch entfernen des `--mqtt` Parameters werden die MQTT Export Funktionalitäten deaktiviert.

Varte Speicher IP Adresse: `192.168.3.30' mit aktivierten MQTT Export:

```
command: ["192.168.3.30", "--mqtt"]
```

Varta Speicher IP Adresse: `10.0.0.10' ohne MQTT Export:

```
command: ["10.0.0.10"]
```

## Starten des Containers:

```bash
docker compose up -d
```

## Beenden des Containers:

```bash
docker compose down
```
