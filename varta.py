import urllib.request
import json
import sys
import time
import configparser
from allthingstalk import Client, Device, IntegerAsset, NumberAsset

config = configparser.ConfigParser()

#Config lesen
try:
   config.read('config')
except:
   print("Fehler beim öffnen des Configfiles")
   quit()

#Definieren des ATT Devices mit Assets
class Varta(Device):
   ul1 = NumberAsset(unit='V')
   ul2 = NumberAsset(unit='V')
   ul3 = NumberAsset(unit='V')
   il1 = NumberAsset(unit='mA')
   il2 = NumberAsset(unit='mA')
   il3 = NumberAsset(unit='mA')
   fnetz = NumberAsset(unit='Hz')
   pv = NumberAsset (unit='W')
   einspeisung = NumberAsset(unit='W')

#ATT Verbindung initialisieren
try:
   client = Client(config['AllThingsTalk']['DeviceToken'])
   device = Varta(client=client, id=config['AllThingsTalk']['DeviceID'])
   ATTconnected=True
except:
   print("Fehler beim Aufbau der ATT Verbindung")
   ATTconnected=False

ems_data_url='http://'+config['DEFAULT']['VartaHost']+'/cgi/ems_data.js'
ems_conf_url='http://'+config['DEFAULT']['VartaHost']+'/cgi/ems_conf.js'

#Hauptprogramm

while (1):
   time.sleep(1)
   print (".")
   try:
      ems_conf = urllib.request.urlopen(ems_conf_url).read()
      error=0
   except:
      print ("Fehler beim holen der EMS Config!")
      error=1

   if error==0:
      ems_conf = ems_conf.decode("utf-8")
      ems_conf = ems_conf.replace("\n","")

      wr_conf=ems_conf[(ems_conf.find("WR_Conf")):]
      wr_conf=wr_conf[:(wr_conf.find(";"))]
      wr_conf='{"' + wr_conf.replace(' = ','":') + '}'

      chrg_conf=ems_conf[(ems_conf.find("Charger_Conf")):]
      chrg_conf=chrg_conf[:(chrg_conf.find(";"))]
      chrg_conf='{"' + chrg_conf.replace(' = ','":') + '}'

      batt_conf=ems_conf[(ems_conf.find("Batt_Conf")):]
      batt_conf=batt_conf[:(batt_conf.find(";"))]
      batt_conf='{"' + batt_conf.replace(' = ','":') + '}'

      modul_conf=ems_conf[(ems_conf.find("Modul_Conf")):]
      modul_conf=modul_conf[:(modul_conf.find(";"))]
      modul_conf='{"' + modul_conf.replace(' = ','":') + '}'

      try:
        ems_data = urllib.request.urlopen(ems_data_url).read()
        error=0
      except:
        print ("Fehler beim holen der EMS Daten!")
        error=1
      if error==0:
         ems_data = ems_data.decode("utf-8")
         ems_data = ems_data.replace("\n","")

         wr_data=ems_data[(ems_data.find("WR_Data")):]
         wr_data=wr_data[:(wr_data.find(";"))]
         wr_data='{"' + wr_data.replace(' = ','":') + '}'

         chrg_data=ems_data[(ems_data.find("Charger_Data")):]
         chrg_data=chrg_data[:(chrg_data.find(";"))]
         chrg_data='{"' + chrg_data.replace(' = ','":') + '}'

         js_wr_data = json.loads(wr_data)
         js_wr_conf = json.loads(wr_conf)

         if config['DEFAULT']['Debug']=='True':
            print("*** EMS ***")
            for x in range (0,(len(js_wr_data['WR_Data']))):
               print ("%s = %s" % (js_wr_conf['WR_Conf'][x], js_wr_data['WR_Data'][x]))
            print("***Charger***")
            js_chrg_data = json.loads(chrg_data)
            js_chrg_conf = json.loads(chrg_conf)
            js_batt_conf = json.loads(batt_conf)
            js_modul_conf = json.loads(modul_conf)
            for y in range (0,(len(js_chrg_data['Charger_Data']))):
               print (">>> CHARGER %s" % y)
               for x in range (0,(len(js_chrg_data['Charger_Data'][y]))):
                  if js_chrg_conf['Charger_Conf'][x] == 'BattData':
                     print (">>> Batterie ")
                     for z in range (0,(len(js_chrg_data['Charger_Data'][y][x]))):
                        if js_batt_conf['Batt_Conf'][z] == 'ModulData':
                           for w in range (0,(len(js_chrg_data['Charger_Data'][y][x][z]))):
                              print (">>> Batteriemodul %s" % w)
                              for v in range (0,(len(js_chrg_data['Charger_Data'][y][x][z][w]))):
                                 print ("%s = %s" % (js_modul_conf['Modul_Conf'][v], js_chrg_data['Charger_Data'][y][x][z][w][v]))
                        else:
                           print ("%s = %s" % (js_batt_conf['Batt_Conf'][z], js_chrg_data['Charger_Data'][y][x][z]))
                  else:
                     print ("%s = %s" % (js_chrg_conf['Charger_Conf'][x], js_chrg_data['Charger_Data'][y][x]))

   if (error==0) and ATTconnected:
      device.ul1 = js_wr_data['WR_Data'][5]
      device.ul2 = js_wr_data['WR_Data'][6]
      device.ul3 = js_wr_data['WR_Data'][7]
      device.il1 = (js_wr_data['WR_Data'][8]*10)
      device.il2 = (js_wr_data['WR_Data'][9]*10)
      device.il3 = (js_wr_data['WR_Data'][10]*10)
      device.fnetz = (js_wr_data['WR_Data'][21]/10)
      device.pv = (js_wr_data['WR_Data'][39])
      device.einspeisung = (js_wr_data['WR_Data'][8]/100*js_wr_data['WR_Data'][5])+(js_wr_data['WR_Data'][9]/100*js_wr_data['WR_Data'][6])+(js_wr_data['WR_Data'][10]/100*js_wr_data['WR_Data'][7])

#ENDE
