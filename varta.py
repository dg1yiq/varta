import urllib.request
import json
import sys
import time
from allthingstalk import Client, Device, IntegerAsset, NumberAsset

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

client = Client('maker:...')
device = Varta(client=client, id='...')

n=0

while (1):
    time.sleep(1)
    n=n+1
    print (n)
    url='http://192.168.3.30/cgi/ems_conf.js'
    try:
       ems_conf = urllib.request.urlopen(url).read()
       error=0
    except:
       print ("Fehler!")
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

        url='http://192.168.3.30/cgi/ems_data.js'
        try:
           ems_data = urllib.request.urlopen(url).read()
           error=0
        except:
           print ("Fehler!")
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

            data = json.loads(wr_data)
            conf = json.loads(wr_conf)

            #print("*** EMS ***")
            #for x in range (0,(len(data['WR_Data']))):
            #   print ("%s = %s" % (conf['WR_Conf'][x], data['WR_Data'][x]))

    if error==0:
       device.ul1 = data['WR_Data'][5]
       device.ul2 = data['WR_Data'][6]
       device.ul3 = data['WR_Data'][7]
       device.il1 = (data['WR_Data'][8]*10)
       device.il2 = (data['WR_Data'][9]*10)
       device.il3 = (data['WR_Data'][10]*10)
       device.fnetz = (data['WR_Data'][21]/10)
       device.pv = (data['WR_Data'][39])
       device.einspeisung = (data['WR_Data'][8]/100*data['WR_Data'][5])+(data['WR_Data'][9]/100*data['WR_Data'][6])+(data['WR_Data'][10]/100*data['WR_Data'][7])
"""
#Details
print("***Charger***")
data = json.loads(chrg_data)
conf = json.loads(chrg_conf)
conf2 = json.loads(batt_conf)
conf3 = json.loads(modul_conf)
for y in range (0,(len(data['Charger_Data']))):
   print (">>> CHARGER %s" % y)
   for x in range (0,(len(data['Charger_Data'][y]))):
      if conf['Charger_Conf'][x] == 'BattData':
         print (">>> Batterie ")
         for z in range (0,(len(data['Charger_Data'][y][x]))):
            if conf2['Batt_Conf'][z] == 'ModulData':
               for w in range (0,(len(data['Charger_Data'][y][x][z]))):
                  print (">>> Batteriemodul %s" % w)
                  for v in range (0,(len(data['Charger_Data'][y][x][z][w]))):
                     print ("%s = %s" % (conf3['Modul_Conf'][v], data['Charger_Data'][y][x][z][w][v]))
            else:
               print ("%s = %s" % (conf2['Batt_Conf'][z], data['Charger_Data'][y][x][z]))
      else:
         print ("%s = %s" % (conf['Charger_Conf'][x], data['Charger_Data'][y][x]))
"""
