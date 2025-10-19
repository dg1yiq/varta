import urllib.request
import json
import time
import configparser


class VartaFunction:

    def __init__(self):
        self.config = configparser.ConfigParser()
        # Config lesen
        try:
            self.config.read('config')
        except:
            print("Fehler beim öffnen des Configfiles")
            quit()

    def main(self):
        print("Programmstart MAIN")
        
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

if __name__ == "__main__":
    mainprogramm = VartaFunction()
    while True:
        try:
            mainprogramm.main()
        except Exception as e:
            print("Exception: %s" % str(e))
        print("Neustart in 60 Sekunden...")
        time.sleep(60)
