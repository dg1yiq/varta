import json
import time
import configparser
import urllib.request
import urllib.error
import re
from prometheus_client import start_http_server, Gauge

def create_gauges_from_final(final, sanitize):
    """
    Erzeugt:
    - inverter_gauges: dict mapping inverter_key -> Gauge
    - charger_gauge: ein Gauge mit Labels (charger,battery,module,metric) für alle Charger-Werte
    """
    inverter_gauges = {}
    for item in final.get('Inverter', []):
        for k in item.keys():
            metric_name = sanitize(f"varta_inverter_{k}")
            # Nur einmal anlegen
            if k not in inverter_gauges:
                inverter_gauges[k] = Gauge(metric_name, f"Varta Inverter {k}")
    charger_gauge = Gauge('varta_charger_value', 'Varta charger metric', ['charger', 'battery', 'module', 'metric'])
    return inverter_gauges, charger_gauge

def update_gauges_from_final(inverter_gauges, charger_gauge, final, sanitize):
    """
    Aktualisiert die Gauges mit Werten aus `final`.
    Nicht-konvertierbare Werte (Strings, IPs, Namen) werden übersprungen.
    """
    # Inverter aktualisieren
    for item in final.get('Inverter', []):
        for k, v in item.items():
            g = inverter_gauges.get(k)
            if g is None:
                continue
            try:
                g.set(float(v))
            except (TypeError, ValueError):
                # nicht-numerisch -> skip
                continue

    # Charger aktualisieren
    for c_idx, charger in enumerate(final.get('Charger', [])):
        # charger ist eine Liste von Einträgen; einige sind {'Batteries': [...]}, andere einfache key->value
        for entry in charger:
            for key, val in entry.items():
                if key == 'Batteries' and isinstance(val, list):
                    # val ist Liste von Batteries (jede Battery ist Liste von dicts)
                    for b_idx, battery in enumerate(val):
                        # battery ist Liste von dicts
                        for b_item in battery:
                            for b_key, b_val in b_item.items():
                                if b_key == 'ModulData' and isinstance(b_val, list):
                                    # b_val ist Liste von Modul-Listen
                                    for module_list in b_val:
                                        for m_idx, module in enumerate(module_list):
                                            # module ist Liste von dicts (jedes dict ein Metric)
                                            for m_item in module:
                                                for m_key, m_val in m_item.items():
                                                    try:
                                                        f = float(m_val)
                                                    except (TypeError, ValueError):
                                                        continue
                                                    charger_gauge.labels(charger=str(c_idx),
                                                                         battery=str(b_idx),
                                                                         module=str(m_idx),
                                                                         metric=sanitize(m_key)).set(f)
                                else:
                                    try:
                                        f = float(b_val)
                                    except (TypeError, ValueError):
                                        continue
                                    charger_gauge.labels(charger=str(c_idx),
                                                         battery=str(b_idx),
                                                         module='',
                                                         metric=sanitize(b_key)).set(f)
                else:
                    # einfacher Charger-Level Eintrag
                    try:
                        f = float(val)
                    except (TypeError, ValueError):
                        continue
                    charger_gauge.labels(charger=str(c_idx),
                                         battery='',
                                         module='',
                                         metric=sanitize(key)).set(f)

def main():
    cfg = configparser.ConfigParser()
    cfg.read('config')
    host = cfg['DEFAULT'].get('VartaHost', 'localhost')
    interval = cfg['DEFAULT'].getint('Intervall', 10)
    prometheus_port = cfg['DEFAULT'].getint('PrometheusPort', 8000)

    ems_conf_url = f'http://{host}/cgi/ems_conf.js'
    ems_data_url = f'http://{host}/cgi/ems_data.js'

    js_wr_conf = None
    js_chrg_conf = None
    js_batt_conf = None
    js_modul_conf = None

    js_wr_data = None
    js_chrg_data = None

    # Prometheus HTTP Server starten
    start_http_server(prometheus_port)

    runcreatgauges = True

    # einmal Konfiguration holen und Gauges anlegen
    try:
        # EMS Konfigurationsdaten holen
        ems_conf = urllib.request.urlopen(ems_conf_url, timeout=10).read().decode('utf-8').replace('\n', '')

        # WR Daten aus EMS Daten extrahieren und zu JSON Format anpassen
        wr_conf = ems_conf[(ems_conf.find("WR_Conf")):]
        wr_conf = wr_conf[:(wr_conf.find(";"))]
        wr_conf = '{"' + wr_conf.replace(' = ', '":') + '}'

        # CHRG Daten aus EMS Daten extrahieren und zu JSON Format anpassen
        chrg_conf = ems_conf[(ems_conf.find("Charger_Conf")):]
        chrg_conf = chrg_conf[:(chrg_conf.find(";"))]
        chrg_conf = '{"' + chrg_conf.replace(' = ', '":') + '}'

        # BATT Daten aus EMS Daten extrahieren und zu JSON Format anpassen
        batt_conf = ems_conf[(ems_conf.find("Batt_Conf")):]
        batt_conf = batt_conf[:(batt_conf.find(";"))]
        batt_conf = '{"' + batt_conf.replace(' = ', '":') + '}'

        # MODUL Daten aus EMS Daten extrahieren und zu JSON Format anpassen
        modul_conf = ems_conf[(ems_conf.find("Modul_Conf")):]
        modul_conf = modul_conf[:(modul_conf.find(";"))]
        modul_conf = '{"' + modul_conf.replace(' = ', '":') + '}'

        # JSON erzeugen
        js_wr_conf = json.loads(wr_conf)
        js_chrg_conf = json.loads(chrg_conf)
        js_batt_conf = json.loads(batt_conf)
        js_modul_conf = json.loads(modul_conf)

    except (ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
        print("Fehler beim holen der EMS Konfigurationsdaten! - %s" % str(e))

    while True:
         # EMS Daten holen
        try:
            ems_data = urllib.request.urlopen(ems_data_url, timeout=10).read().decode('utf-8').replace('\n', '')

            wr_data = ems_data[(ems_data.find("WR_Data")):]
            wr_data = wr_data[:(wr_data.find(";"))]
            wr_data = '{"' + wr_data.replace(' = ', '":') + '}'

            chrg_data = ems_data[(ems_data.find("Charger_Data")):]
            chrg_data = chrg_data[:(chrg_data.find(";"))]
            chrg_data = '{"' + chrg_data.replace(' = ', '":') + '}'

            # JSON erzeugen
            js_wr_data = json.loads(wr_data)
            js_chrg_data = json.loads(chrg_data)

            final = {}

            # add WR_Data to final
            final['Inverter'] = []
            for x in range(0, (len(js_wr_data['WR_Data']))):
                # Append Key data to final
                final['Inverter'].append({js_wr_conf['WR_Conf'][x]:js_wr_data['WR_Data'][x]})

            charger = []
            for y in range(0, (len(js_chrg_data['Charger_Data']))):
                # For every Charger add an Arry to charger
                charger.append([])
                # Check for Chield Elements
                battery = []
                for x in range(0, (len(js_chrg_data['Charger_Data'][y]))):
                    if js_chrg_conf['Charger_Conf'][x] == 'BattData':
                        module = []
                        for z in range(0, (len(js_chrg_data['Charger_Data'][y][x]))):
                            if js_batt_conf['Batt_Conf'][z] == 'ModulData':
                                module.append([])
                                for w in range(0, (len(js_chrg_data['Charger_Data'][y][x][z]))):
                                    for v in range(0, (len(js_chrg_data['Charger_Data'][y][x][z][w]))):
                                        # Module Data
                                        module[w].append({js_modul_conf['Modul_Conf'][v]:js_chrg_data['Charger_Data'][y][x][z][w][v]})
                                battery.append({'ModulData': module})
                            else:
                                battery.append({js_batt_conf['Batt_Conf'][z]:js_chrg_data['Charger_Data'][y][x][z]})
                        # Append Battery Data
                        charger[y].append({'Batteries': battery})
                    else:
                        # Append Inverter Data
                        charger[y].append({js_chrg_conf['Charger_Conf'][x]: js_chrg_data['Charger_Data'][y][x]})

            final['Charger'] = charger

            # Check if Run Create Gauges
            if runcreatgauges:
                inverter_gauges, charger_gauge = create_gauges_from_final(final, lambda s: re.sub(r'[^a-zA-Z0-9_]', '_', s.lower()))
                runcreatgauges = False

            # Update Gauges
            if 'inverter_gauges' not in locals() or 'charger_gauge' not in locals():
                inverter_gauges, charger_gauge = create_gauges_from_final(final, lambda s: re.sub(r'[^a-zA-Z0-9_]', '_', s.lower()))

        except (ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
            print("Fehler beim holen der EMS Daten! - %s" % str(e))

        # Warte Intervall
        time.sleep(interval)

if __name__ == '__main__':
    main()