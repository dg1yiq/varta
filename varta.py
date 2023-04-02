import urllib.request
import json
import time
import configparser
from allthingstalk import Client, Device, IntegerAsset, NumberAsset


# Definieren des ATT Devices mit Assets
class Varta(Device):
    fnetz = NumberAsset(unit='Hz')
    pv = NumberAsset(unit='W')
    einspeisung = NumberAsset(unit='W')


class VartaFunction:

    def __init__(self):
        self.ATTConnected = False
        self.config = configparser.ConfigParser()
        self.device = None
        self.client = None
        # Config lesen
        try:
            self.config.read('config')
        except:
            print("Fehler beim öffnen des Configfiles")
            quit()

    def main(self):
        print("Programmstart MAIN")
        # ATT Verbindung initialisieren
        devicetoken = self.config.get('AllThingsTalk', 'DeviceToken', fallback=None)
        deviceid = self.config.get('AllThingsTalk', 'DeviceID', fallback=None)

        if "also" in devicetoken:
            api = "also.allthingstalk.io"
        elif "maker" in devicetoken:
            api = "api.allthingstalk.io"
        else:
            api = None
        if (devicetoken is None) or (len(devicetoken) < 40) or (api is None):
            print("ATT DeviceToken falsch konfiguriert?!")
        if (deviceid is None) or (len(deviceid) != 24):
            print("ATT DeviceID falsch konfiguriert?!")
        try:
            self.client = Client(devicetoken, api=api)
            self.device = Varta(client=self.client, id=deviceid)
            self.ATTConnected = True
        except Exception as e:
            print("Fehler beim Aufbau der ATT Verbindung - %s" % e)
            self.ATTConnected = False
        
        ems_data_url = 'http://' + self.config['DEFAULT']['VartaHost'] + '/cgi/ems_data.js'
        ems_conf_url = 'http://' + self.config['DEFAULT']['VartaHost'] + '/cgi/ems_conf.js'

        js_wr_conf = None
        js_chrg_conf = None
        js_batt_conf = None
        js_modul_conf = None

        js_wr_data = None
        js_chrg_data = None

        # EMS Configuration brauchen wir nur einmal zu holen!
        count = 1
        while count < 4:
            try:
                print("Hole EMS Konfigurationsdaten - Versuch %s" % count)
                # Die EMS Config URL enthält Daten:
                # WR_Conf = Wechselrichter Konfiguration
                # CHRG_Conf = Lader Konfiguration
                # BATT_Conf = Batterie Konfiguration
                # MODUL_Cons = Modul Konfiguration

                # EMS Daten holen
                ems_conf = urllib.request.urlopen(ems_conf_url).read()
                ems_conf = ems_conf.decode("utf-8")
                ems_conf = ems_conf.replace("\n", "")

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

                # geschaft...
                print("EMS Konfigurationsdaten erfolgreich geholt")
                break
            except (ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
                print("Fehler beim holen der EMS Konfigurationsdaten! - %s" % str(e))
                if count == 3:
                    print("Fehler beim holen der EMS Konfigurationsdaten - Program Abbruch!")
                    exit()
                else:
                    count += 1

        while True:
            # hier ziehen wir die Bremse :-)
            time.sleep(self.config.getint('DEFAULT', 'Intervall'))

            try:
                ems_data = urllib.request.urlopen(ems_data_url).read()
                ems_data = ems_data.decode("utf-8")
                ems_data = ems_data.replace("\n", "")

                wr_data = ems_data[(ems_data.find("WR_Data")):]
                wr_data = wr_data[:(wr_data.find(";"))]
                wr_data = '{"' + wr_data.replace(' = ', '":') + '}'

                chrg_data = ems_data[(ems_data.find("Charger_Data")):]
                chrg_data = chrg_data[:(chrg_data.find(";"))]
                chrg_data = '{"' + chrg_data.replace(' = ', '":') + '}'

                # JSON erzeugen
                js_wr_data = json.loads(wr_data)
                js_chrg_data = json.loads(chrg_data)

                if self.config.getboolean('DEFAULT', 'Debug') is True:
                    print("*** EMS/Inverter ***")
                    for x in range(0, (len(js_wr_data['WR_Data']))):
                        print("%s = %s" % (js_wr_conf['WR_Conf'][x], js_wr_data['WR_Data'][x]))
                    print("***Charger***")
                    for y in range(0, (len(js_chrg_data['Charger_Data']))):
                        print(">>> CHARGER %s" % y)
                        for x in range(0, (len(js_chrg_data['Charger_Data'][y]))):
                            if js_chrg_conf['Charger_Conf'][x] == 'BattData':
                                print(">>> Battery ")
                                for z in range(0, (len(js_chrg_data['Charger_Data'][y][x]))):
                                    if js_batt_conf['Batt_Conf'][z] == 'ModulData':
                                        for w in range(0, (len(js_chrg_data['Charger_Data'][y][x][z]))):
                                            print(">>> Battery unit %s" % w)
                                            for v in range(0, (len(js_chrg_data['Charger_Data'][y][x][z][w]))):
                                                print("%s = %s" % (js_modul_conf['Modul_Conf'][v],
                                                                   js_chrg_data['Charger_Data'][y][x][z][w][v]))
                                    else:
                                        print("%s = %s" % (
                                            js_batt_conf['Batt_Conf'][z], js_chrg_data['Charger_Data'][y][x][z]))
                            else:
                                print("%s = %s" % (js_chrg_conf['Charger_Conf'][x], js_chrg_data['Charger_Data'][y][x]))
            except (ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
                print("Fehler beim holen der EMS Daten! - %s" % str(e))

            if self.ATTConnected:
                self.device.fnetz = (js_wr_data['WR_Data'][21] / 10)
                self.device.pv = (js_wr_data['WR_Data'][39])
                self.device.einspeisung = (js_wr_data['WR_Data'][8] / 100 * js_wr_data['WR_Data'][5]) + \
                                          (js_wr_data['WR_Data'][9] / 100 * js_wr_data['WR_Data'][6]) + \
                                          (js_wr_data['WR_Data'][10] / 100 * js_wr_data['WR_Data'][7])


if __name__ == "__main__":
    mainprogramm = VartaFunction()
    while True:
        try:
            mainprogramm.main()
        except (ConnectionError, ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError) as e:
            print("Allgemeiner Fehler, vermutlich ATT! - %s" % str(e))
        print("Cleanup...")
        mainprogramm.ATTConnected = False
        mainprogramm.device = None
        mainprogramm.client = None
        print("Neustart in 60 Sekunden...")
        time.sleep(60)
