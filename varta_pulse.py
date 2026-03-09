import json
import time

import requests
from requests import Response, Session
import argparse
import re
from typing import Dict, List, Any
from prometheus_client import start_http_server, Gauge
from mqtt_pulse import MQTTClient, generate_mqtt_uplink, generate_mqtt_discovery


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

def main(host: str,
         prometheus_port: int,
         interval: int,
         mqtt: bool = False,
         mqtt_host: str = None,
         mqtt_port: int = 1883,
         mqtt_username: str = None,
         mqtt_password: str = None,
         varta_user: str = "user1",
         varta_password: str = None) -> None:

    session = Session()

    def _check_logged_in():
        check_url = f"http://{host}/cgi/user"
        pass_url = f"http://{host}/cgi/login"
        response = session.get(check_url, timeout=3)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Check if Eyception is due to an 403 Forbidden, which indicates not logged in
            if e.response.status_code == 403:
                login_data = {"user": varta_user, "password": varta_password}
                response = session.post(pass_url, login_data, timeout=3)
                response.raise_for_status()
                return response.status_code == 200

        values = re.compile("userlevel = ([0-9]+)")
        results = values.findall(response.text)
        print(results)
        if "3" in results:
            # already logged in
            return True

        login_data = {"user": varta_user, "password": varta_password}
        response = session.post(pass_url, login_data, timeout=3)
        response.raise_for_status()
        return response.status_code == 200

    def _request_data(url) -> Response:
        try:
            # Check if a password is set
            if varta_password:
                # Password is set so we check if already logged in
                _check_logged_in()
            return session.get(url, timeout=3)
        except Exception as e:
            raise ValueError(f"Error Gettings Data from {url}") from e

    if not host:
        raise SystemExit('Fehler: Das Argument `host` ist zwingend erforderlich.')

    print(f'\nStarte Varta Exporter für Speicher: {host} auf Prometheus Port {prometheus_port} mit Intervall {interval} Sekunden.')

    if varta_password:
        print(f'Mit Varta User: {varta_user} und Passwort: {varta_password}')

    mqtt_client = None

    if mqtt is True:
        print(f'Main: MQTT Exporter aktiviert')
        mqtt_client = MQTTClient(hostname=mqtt_host, port=mqtt_port, username=mqtt_username, password=mqtt_password)
        mqtt_client.client.loop_start()
        generate_mqtt_discovery(mqtt_client)

    data_url = f'http://{host}/cgi/data'

    # Prometheus HTTP Server starten
    start_http_server(prometheus_port)

    struct = None
    gauge = None
    gauge_children = None

    nextrun = time.time() + interval

    while True:
        # Warte bis zum nächsten Zyklustakt
        if time.time() < nextrun:
            time.sleep(0.1)
            continue

        # Rearm nextrun immediately to avoid drift, auch wenn die Datenabfrage länger dauert als das Intervall
        nextrun = time.time() + interval

        # EMS Daten holen, da sie sich schnell ändern können, aber nur einmal pro Zyklus
        data = ''
        try:
            response = _request_data(data_url)
            response.raise_for_status()
            data = response.text.replace('\n', '')
        except Exception as e:
            raise e
            print("A", end='', flush=True)
            continue

        # Die Rohdaten liegen als Json vor, aber in einem String. Also erst Json parsen, dann den String als Json parsen.
        try:
            print(data)
            final = json.loads(data)
        except Exception as e:
            print("B", end='', flush=True)
            continue

        if struct is None:
            # Erster Zyklus: Struktur aus final erzeugen und Gauges anlegen
            struct = create_structure_from_final(final)
            gauge, gauge_children = create_gauges_from_structure(struct)
            # Optional sofort Gauges initial füllen
            write_gauges_from_children(gauge_children, struct)
        else:
            # Prüfe ob sich die Struktur geändert hat (neue Metrics oder Types) und erweitere sie ggf.
            try:
                # Stelle sicher, dass gauge_children initialisiert sind
                if gauge is None:
                    gauge, gauge_children = create_gauges_from_structure(struct)

                for metric, entries in final.items():
                    # wenn neue Metric, lege Eintrag in gauge_children an
                    if metric not in gauge_children:
                        gauge_children[metric] = {}
                    for e in entries:
                        for type_name in e.keys():
                            # Wenn child noch nicht existiert, erstelle es
                            if gauge_children.get(metric, {}).get(type_name) is None:
                                try:
                                    child = gauge.labels(metric=metric, type=type_name)
                                except Exception:
                                    child = None
                                gauge_children[metric][type_name] = child
            except Exception:
                # Wenn beim Erweitern etwas schief geht, ignoriere und fahre normal fort
                pass

            # Folgende Zyklen: neue Werte an bestehende Struktur anhängen und Gauges aktualisieren
            append_final_to_structure(struct, final)
            write_gauges_from_children(gauge_children, struct)

        if mqtt is True:
            generate_mqtt_uplink(final, mqtt_client)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Varta Exporter')
    parser.add_argument('host', help='IP-Adresse oder Hostname des Varta Speichers (z.B. 192.168.3.30)')
    parser.add_argument('--prometheus-port', type=int, default=8000,
                        help='Prometheus HTTP Port (Default 8000)')
    parser.add_argument('--interval', type=int, default=1,
                        help='Abfrageintervall in Sekunden (Default 1)')
    parser.add_argument('--mqtt', action='store_true', help='MQTT Exporter aktivieren')
    parser.add_argument('--mqtt-host', type=str, default=None, help='Hostname oder IP des MQTT Brokers')
    parser.add_argument('--mqtt-port', type=int, default=1883,)
    parser.add_argument('--mqtt-username', type=str, default=None, help='MQTT Username')
    parser.add_argument('--mqtt-password', type=str, default=None, help='MQTT Password')
    parser.add_argument('--varta-user', type=str, default="user1", help='Varta User (Default: user1)')
    parser.add_argument('--varta-password', type=str, default=None, help='Varta Password')
    args = parser.parse_args()
    main(args.host, args.prometheus_port, args.interval, args.mqtt, args.mqtt_host, args.mqtt_port, args.mqtt_username, args.mqtt_password, args.varta_user, args.varta_password)