import json
import time
import urllib.request
import urllib.error
import argparse
from typing import Dict, List, Any, Tuple
from prometheus_client import start_http_server, Gauge

# Neue Funktion: hänge `final`-Werte in die bestehende Struktur an
def append_final_to_structure(structure: Dict[str, List[Dict[str, List[Any]]]],
                              parsed: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, List[Any]]]]:
    """
    Fügt die Werte aus `parsed` (deinem `final`-Dict) zyklisch an `structure` an.
    Wenn structure leer ist, wird sie initialisiert und zurückgegeben.
    """
    if structure is None:
        return create_structure_from_final(parsed)

    for metric, entries in parsed.items():
        for e in entries:
            for type_name, val in e.items():
                update_metric(structure, metric, type_name, val)
    return structure

def create_gauges_from_structure(structure: Dict[str, List[Dict[str, List[Any]]]]
                                ) -> tuple[Gauge, Dict[str, Dict[str, Any]]]:
    """
    Erzeugt einen einzigen Gauge mit Labels 'metric' und 'type' und
    legt für jede Metric/Type-Kombination das Child (labels(...)) an.
    Rückgabe: (base_gauge, children_map[metric][type] -> child)
    """
    g = Gauge('varta_metric', 'Varta metric values', ['metric', 'type'])
    children: Dict[str, Dict[str, Any]] = {}
    for metric, entries in structure.items():
        children[metric] = {}
        for entry in entries:
            for type_name in entry.keys():
                try:
                    children[metric][type_name] = g.labels(metric=metric, type=type_name)
                except Exception:
                    children[metric][type_name] = None
    return g, children

def write_gauges_from_children(children: Dict[str, Dict[str, Any]],
                               structure: Dict[str, List[Dict[str, List[Any]]]]) -> None:
    """
    Schreibt die letzten Werte aus structure in die vorab angelegten Children.
    """
    for metric, entries in structure.items():
        for entry in entries:
            for type_name, values in entry.items():
                if not values:
                    continue
                val = values[-1]
                if isinstance(val, bool):
                    num = 1.0 if val else 0.0
                else:
                    try:
                        num = float(val)
                    except (TypeError, ValueError):
                        continue
                child = children.get(metric, {}).get(type_name)
                if child is not None:
                    try:
                        child.set(num)
                    except Exception:
                        pass

def _find_type_entry(metric_list: List[Dict[str, List[Any]]], type_name: str):
    for entry in metric_list:
        if type_name in entry:
            return entry
    return None

def update_metric(structure: Dict[str, List[Dict[str, List[Any]]]],
                  metric: str,
                  type_name: str,
                  value: Any) -> None:
    """
    Fügt `value` zu structure[metric][type_name] hinzu.
    Legt Metric und Type an, falls nicht vorhanden.
    Wenn `value` eine Liste ist, werden die Elemente angehängt.
    """
    if metric not in structure:
        structure[metric] = []
    metric_list = structure[metric]

    entry = _find_type_entry(metric_list, type_name)
    if entry is None:
        entry = {type_name: []}
        metric_list.append(entry)

    if isinstance(value, list):
        entry[type_name].extend(value)
    else:
        entry[type_name].append(value)

def create_structure_from_final(parsed: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, List[Any]]]]:
    """
    Erzeugt die gewünschte Struktur aus dem bereits erzeugten `final`-Dict.
    Beispiel input:
      { "Inverter": [{"EMS PExtra": 0}, {"EMS UG": -4000}], ... }
    Ergebnis:
      { "Inverter": [{"EMS PExtra": [0]}, {"EMS UG": [-4000]}], ... }
    Falls derselbe Type mehrfach vorkommt, werden die Werte in einer Liste zusammengeführt.
    """
    structure: Dict[str, List[Dict[str, List[Any]]]] = {}
    for metric, entries in parsed.items():
        for e in entries:
            for type_name, val in e.items():
                update_metric(structure, metric, type_name, val)
    return structure

def main(host: str, prometheus_port: int, interval: int):
    if not host:
        raise SystemExit('Fehler: Das Argument `host` ist zwingend erforderlich.')

    print(f'\nStarte Varta Exporter für Speicher: {host} auf Prometheus Port {prometheus_port} mit Intervall {interval} Sekunden.')

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

    struct = None
    gauge = None
    gauge_children = None

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

    except Exception as e:
        print("Fehler beim holen der EMS Konfigurationsdaten! - %s" % str(e))

    while True:
        ems_data = ''
        try:
            ems_data = urllib.request.urlopen(ems_data_url, timeout=10).read().decode('utf-8').replace('\n', '')
        except Exception as e:
            print("X", end='', flush=True)
            time.sleep(interval)
            continue

        try:
            # Check that ems_data containce the required data
            if ems_data.find("WR_Data") == -1 or ems_data.find("Charger_Data") == -1 or ems_data == '':
                time.sleep(interval)
                continue

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
            # Check if it is a list
            if not isinstance(js_wr_data['WR_Data'], list):
                time.sleep(interval)
                continue

            for x in range(0, (len(js_wr_data['WR_Data']))):
                # Append Key data to final
                final['Inverter'].append({js_wr_conf['WR_Conf'][x]:js_wr_data['WR_Data'][x]})

            # Check that Charger_Data is a list
            if not isinstance(js_chrg_data['Charger_Data'], list):
                time.sleep(interval)
                continue

            for y in range(0, (len(js_chrg_data['Charger_Data']))):
                # For every Charger add an Arry to charger
                charger = []
                #
                for x in range(0, (len(js_chrg_data['Charger_Data'][y]))):
                    battery = []
                    battcount = 0
                    if js_chrg_conf['Charger_Conf'][x] == 'BattData':
                        # Check for Battery Elements
                        for z in range(0, (len(js_chrg_data['Charger_Data'][y][x]))):
                            if js_batt_conf['Batt_Conf'][z] == 'ModulData':
                                for w in range(0, (len(js_chrg_data['Charger_Data'][y][x][z]))):
                                    module = []
                                    modulecount = 0
                                    for v in range(0, (len(js_chrg_data['Charger_Data'][y][x][z][w]))):
                                        # Module Data
                                        module.append({js_modul_conf['Modul_Conf'][v]:js_chrg_data['Charger_Data'][y][x][z][w][v]})
                                    final[f'Charger{y}_Battery{battcount}_Module{modulecount}'] = module
                                    modulecount += 1
                            else:
                                battery.append({js_batt_conf['Batt_Conf'][z]:js_chrg_data['Charger_Data'][y][x][z]})
                        # Append Battery Data
                        final[f'Charger{y}_Battery{battcount}'] = battery
                        battcount += 1
                    else:
                        # Append Inverter Data
                        charger.append({js_chrg_conf['Charger_Conf'][x]: js_chrg_data['Charger_Data'][y][x]})
                final[f'Charger{y}'] = charger

            print(".", end='', flush=True)

        except Exception as e:
            print("E", end='', flush=True)
            time.sleep(interval)
            continue

        if struct is None:
            # Erster Zyklus: Struktur aus final erzeugen und Gauges anlegen
            struct = create_structure_from_final(final)
            gauge, gauge_children = create_gauges_from_structure(struct)
            # Optional sofort Gauges initial füllen
            write_gauges_from_children(gauge_children, struct)
        else:
            # Folgende Zyklen: neue Werte an bestehende Struktur anhängen und Gauges aktualisieren
            append_final_to_structure(struct, final)
            write_gauges_from_children(gauge_children, struct)

        # Warte Intervall
        time.sleep(interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Varta Exporter')
    parser.add_argument('host', help='IP-Adresse oder Hostname des Varta Speichers (z.B. 192.168.3.30)')
    parser.add_argument('--prometheus-port', '-p', type=int, default=8000,
                        help='Prometheus HTTP Port (Default 8000)')
    parser.add_argument('--interval', '-i', type=int, default=15,
                        help='Abfrageintervall in Sekunden (Default 15)')
    args = parser.parse_args()
    main(args.host, args.prometheus_port, args.interval)