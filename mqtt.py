import paho.mqtt.client as mqttclient
from typing import Any, Iterable
from pathlib import Path
import uuid
import json


class MQTTClient():
    def on_disconnect(self, client, userdata,  rc):
        print("MQTT: Disconnected")

    def on_program_close(self):
        print("MQTT: On_Program_Close")
        self.client.loop_stop(force=True)
        print("MQTT: On_Program_Close done")

    def on_message(self, client, userdata, message):
        # Should not happen, because we do not subscribe to any topic, but we need to implement this function to avoid errors
        pass

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT: Verbindung erfolgreich hergestellt...")
        else:
            print("MQTT: Verbindung fehlgeschlagen mit Code #%s..." % str(rc))

    def __init__(self, hostname:str = None, port:int = 1883, username:str = None, password:str = None):
        # Cleint ID set to Varta + random suffix (letzte 4 Hex-Zeichen) to avoid conflicts with other clients
        # Achtung: nur 4 Zeichen reduziert die Einzigartigkeit stark; bei Bedarf mehr Zeichen verwenden.
        self.id = "Varta" + uuid.uuid4().hex[-4:]
        self.client = mqttclient.Client(client_id=self.id)
        self.client.on_disconnect = self.on_disconnect
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        if hostname is not None:
            if username is not None and password is not None:
                self.client.username_pw_set(username, password)
            # Use external MQTT Broker
            try:
                self.client.connect(hostname, port, 60)
            except Exception as e:
                print("MQTT: External Broker - %s" % e)
                raise("MQTT: External Broker - %s" % e)
        else:
            #
            # Use internal MQTT Broker
            #
            if Path('/usr/src/.insideDocker').exists():
                print("MQTT: We are inside Docker...")
                # Inside Docker we need to connect to the host.docker.internal
                try:
                    self.client.connect('host.docker.internal', 1883, 60)
                except Exception as e:
                    print("MQTT: inside Docker Broker - %s" % e)
                    raise("MQTT: inside Docker Broker - %s" % e)
            else:
                print("MQTT: We are NOT inside Docker...")
                # Outside Docker we can connect to localhost
                try:
                    self.client.connect('127.0.0.1', 1883, 60)
                except Exception as e:
                    print("MQTT: localhost Broker - %s" % e)
                    raise("MQTT: localhost Broker - %s" % e)

    # homeassistant/sensor/<device_id>/<sensor_id>/config
    def upstreamdiscovery(self, deviceid:str = None, sensorid:str = None, config:str = None, retain:bool = False):
        if deviceid is not None and sensorid is not None and config is not None:
            self.client.publish(topic=f"homeassistant/sensor/{deviceid}/{sensorid}/config",
                                payload=config,
                                qos=0,
                                retain=retain)

    # homeassistant/sensor/<device_id>/<sensor_id>/state
    def upstreamstate(self, deviceid:str = None, sensorid:str = None, state:str = None, retain:bool = False):
        if deviceid is not None and sensorid is not None and state is not None:
            self.client.publish(topic=f"/varta/{deviceid}/{sensorid}/state",
                                payload=state,
                                qos=0,
                                retain=retain)

def generate_mqtt_uplink(werte: dict = None, mqttclient: MQTTClient = None):
    if werte is None or not isinstance(werte, dict):
        print("MQTT: generate_mqtt_uplink - No data to generate MQTT uplink")
        return

    if mqttclient is None:
        print("MQTT: generate_mqtt_discovery - No MQTT client provided")
        return

    value = next((e['EGrid_AC_DC'] for e in werte.get('Energy', []) if isinstance(e, dict) and 'EGrid_AC_DC' in e), None)
    if value is not None:
        mqttclient.upstreamstate(deviceid="element", sensorid="grid_ac_dc_work_total", state=str(value), retain=False)

    value = next((e['EGrid_DC_AC'] for e in werte.get('Energy', []) if isinstance(e, dict) and 'EGrid_DC_AC' in e), None)
    if value is not None:
        mqttclient.upstreamstate(deviceid="element", sensorid="grid_dc_ac_work_total", state=str(value), retain=False)

    value = next((e['EWr_AC_DC'] for e in werte.get('Energy', []) if isinstance(e, dict) and 'EWr_AC_DC' in e), None)
    if value is not None:
        mqttclient.upstreamstate(deviceid="element", sensorid="battery_ac_dc_work_total", state=str(value), retain=False)

    value = next((e['EWr_DC_AC'] for e in werte.get('Energy', []) if isinstance(e, dict) and 'EWr_DC_AC' in e), None)
    if value is not None:
        mqttclient.upstreamstate(deviceid="element", sensorid="battery_dc_ac_work_total", state=str(value), retain=False)

    u1 = next((e['U Verbund L1'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Verbund L1' in e), None)
    u2 = next((e['U Verbund L2'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Verbund L2' in e), None)
    u3 = next((e['U Verbund L3'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Verbund L3' in e), None)
    i1 = next((e['I Verbund L1'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Verbund L1' in e), None)
    i2 = next((e['I Verbund L2'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Verbund L2' in e), None)
    i3 = next((e['I Verbund L3'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Verbund L3' in e), None)
    p1 = None
    p2 = None
    p3 = None
    if u1 is not None and i1 is not None:
        p1 = u1 * i1/100
    if u2 is not None and i2 is not None:
        p2 = u2 * i2/100
    if u3 is not None and i3 is not None:
        p3 = u3 * i3/100
    if p1 and p2 and p3 is not None:
        p_total = (p1 + p2 + p3) * -1
        mqttclient.upstreamstate(deviceid="element", sensorid="grid_power", state=str(p_total), retain=False)

    u1 = next((e['U Insel L1'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Insel L1' in e), None)
    u2 = next((e['U Insel L2'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Insel L2' in e), None)
    u3 = next((e['U Insel L3'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'U Insel L3' in e), None)
    i1 = next((e['I Insel L1'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Insel L1' in e), None)
    i2 = next((e['I Insel L2'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Insel L2' in e), None)
    i3 = next((e['I Insel L3'] for e in werte.get('Inverter', []) if isinstance(e, dict) and 'I Insel L3' in e), None)
    p1 = None
    p2 = None
    p3 = None
    if u1 is not None and i1 is not None:
        p1 = u1 * i1 / 100
    if u2 is not None and i2 is not None:
        p2 = u2 * i2 / 100
    if u3 is not None and i3 is not None:
        p3 = u3 * i3 / 100
    if p1 and p2 and p3 is not None:
        p_total = (p1 + p2 + p3) * -1
        mqttclient.upstreamstate(deviceid="element", sensorid="battery_power", state=str(p_total), retain=False)


def generate_mqtt_discovery(mqttclient: MQTTClient = None):
    def dicoverypayload(deviceid: str = None, sensorid: str = None, name: str = None, unit: str = None,
                        device_class: str = None, state_class: str = None):
        if deviceid is not None and sensorid is not None and name is not None:
            payload = {
                "name": name,
                "state_topic": f"/varta/{deviceid}/{sensorid}/state",
                "unique_id": f"{deviceid}_{sensorid}",
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": state_class,
                "device": {
                    "identifiers": [deviceid],
                    "name": "Varta Element",
                    "manufacturer": "Varta"
                }
            }
            return json.dumps(payload)
        else:
            print("MQTT: generate_mqtt_discovery - Missing parameters for discovery payload")
            return None

    if mqttclient is None:
        print("MQTT: generate_mqtt_discovery - No MQTT client provided")
        return

    deviceid = "element"

    sensorid = "grid_ac_dc_work_total"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Netzbezug Total", unit="Wh", device_class="energy", state_class="total_increasing")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)

    sensorid = "grid_dc_ac_work_total"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Einspeisung Total", unit="Wh", device_class="energy", state_class="total_increasing")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)

    sensorid = "battery_ac_dc_work_total"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Ladung Total", unit="Wh", device_class="energy", state_class="total_increasing")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)

    sensorid = "battery_dc_ac_work_total"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Entladung Total", unit="Wh", device_class="energy", state_class="total_increasing")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)

    # Grid Power = Positiv: Netzbezug, Negativ: Einspeisung
    sensorid = "grid_power"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Netzbezug", unit="W", device_class="power", state_class="measurement")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)

    # Battery Power = Positiv: Entladung, Negativ: Ladung
    sensorid = "battery_power"
    payload = dicoverypayload(deviceid=deviceid, sensorid=sensorid, name="Batterieentladung", unit="W", device_class="power", state_class="measurement")
    mqttclient.upstreamdiscovery(deviceid=deviceid, sensorid=sensorid, config=payload, retain=True)