import json
import time
import configparser
import urllib.request
import urllib.error
import re
from prometheus_client import start_http_server, Gauge

def sanitize(name: str) -> str:
    return re.sub(r'[^0-9a-zA-Z_]', '_', name).lower()

def parse_js_vars(text: str):
    # findet Muster wie VarName = { ... };
    vars = {}
    for m in re.finditer(r'(\w+)\s*=\s*(\{.*?\})\s*;', text, re.DOTALL):
        name, js = m.group(1), m.group(2)
        try:
            vars[name] = json.loads(js)
        except Exception:
            pass
    return vars

def build_gauges_from_conf(conf):
    # erwartet z.B. conf['WR_Conf'] = [ 'Voltage', 'Current', ... ]
    gauges = {}
    for key, arr in conf.items():
        if isinstance(arr, list):
            for i, name in enumerate(arr):
                metric_name = sanitize(f"varta_{key}_{name}")
                gauges[(key, i)] = Gauge(metric_name, f"Varta metric {key}.{name}")
    return gauges

def update_gauges(gauges, data):
    # data z.B. {'WR_Data': [ ... ], 'Charger_Data': [...]}
    for (key, idx), gauge in list(gauges.items()):
        arr = data.get(key)
        if arr is None:
            continue
        # bei WR_Data: arr ist Liste einfacher Werte
        value = arr[idx]
        gauge.set(float(value))

def main():
    cfg = configparser.ConfigParser()
    cfg.read('config')
    host = cfg['DEFAULT'].get('VartaHost', 'localhost')
    interval = cfg['DEFAULT'].getint('Intervall', 10)
    prometheus_port = cfg['DEFAULT'].getint('PrometheusPort', 8000)

    ems_conf_url = f'http://{host}/cgi/ems_conf.js'
    ems_data_url = f'http://{host}/cgi/ems_data.js'

    # Prometheus HTTP Server starten
    start_http_server(prometheus_port)

    # einmal Konfiguration holen und Gauges anlegen
    try:
        raw = urllib.request.urlopen(ems_conf_url, timeout=10).read().decode('utf-8')
        vars = parse_js_vars(raw)
        # Beispiel: WR_Conf, Charger_Conf, Batt_Conf, Modul_Conf
        gauges = {}
        for name in ('WR_Conf', 'Charger_Conf', 'Batt_Conf', 'Modul_Conf'):
            if name in vars:
                # vars[name] ist ein dict mit z.B. 'WR_Conf': [ ... ] oder direkt Liste
                # normalize: falls wrapper-dict, finden wir Liste im ersten Wert
                val = vars[name]
                if isinstance(val, dict):
                    # nehme ersten Listeneintrag falls vorhanden
                    for v in val.values():
                        if isinstance(v, list):
                            gauges.update(build_gauges_from_conf({name: v}))
                            break
                elif isinstance(val, list):
                    gauges.update(build_gauges_from_conf({name: val}))
    except Exception as e:
        print("Fehler beim Holen der Konfig:", e)
        gauges = {}

    # Loop: Daten holen und Gauges aktualisieren
    while True:
        try:
            raw = urllib.request.urlopen(ems_data_url, timeout=10).read().decode('utf-8')
            vars = parse_js_vars(raw)
            # vars könnte 'WR_Data' und 'Charger_Data' enthalten
            # update_gauges erwartet keys wie 'WR_Data' etc.
            update_gauges(gauges, vars)
        except urllib.error.URLError as e:
            print("Netzwerkfehler:", e)
        except Exception as e:
            print("Fehler beim Verarbeiten:", e)
        time.sleep(interval)

if __name__ == '__main__':
    main()