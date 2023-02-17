#           SLS gateway Plugin
#
#           Author:     DCRM, 2023
#
"""
<plugin key="Slsys" name="SLS gateway" author="DCRM" version="0.0.1" wikilink="https://slsys.github.io/Gateway/README_rus.html" externallink="https://github.com/william-aqn/slsys-domoticz">
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="192.168.1.20"/>
        <param field="Port" label="Port" width="30px" required="true" default="80"/>
        <param field="Password" label="Token" width="250px" default=""/>

        <param field="Mode2" label="Radio" width="240px" default="jazz#http://jazz.streamr.ru/jazz-64.mp3|http://jazz.streamr.ru/jazz-64.mp3"/>
        
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import sys
import json
from urllib import request, parse


class BasePlugin:
    sProtocol = "HTTP"
    
    # Статус аудио
    audioState = 0
    audioVolumeLevel=0
    audioUrl = ""
    
    # Список устройств
    UNITS = {
        'Audio': 1,
        'Volume': 2,
        'UrlSelector': 3,
        'Reboot': 5
    }
    
    def buildUrlSelectorOptions(self):
        Options = {"LevelActions": "||||",
                       "LevelNames": "Auto|Silent|Medium|High",
                       "LevelOffHidden": "false",
                       "SelectorStyle": "0"
                      }
        return Options
    
    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            DumpConfigToLog()

        # Создаём устройства
        if self.UNITS['Audio'] not in Devices:
            Domoticz.Device(Name="Audio", Unit=self.UNITS['Audio'], Type=17,  Switchtype=17).Create()
            
        if self.UNITS['Volume'] not in Devices:
            Domoticz.Device(Name="Volume", Unit=self.UNITS['Volume'], TypeName='Dimmer').Create()
            
        if self.UNITS['UrlSelector'] not in Devices:
            Domoticz.Device(Name="Radio stations", Unit=self.UNITS['UrlSelector'], TypeName='Selector Switch', Options={}).Create()
        # Обновляем станции
        if self.UNITS['UrlSelector'] in Devices:
            Devices[self.UNITS['UrlSelector']].Update(Options=self.buildUrlSelectorOptions())
                                    
        if self.UNITS['Reboot'] not in Devices:
            Domoticz.Device(Name="Reboot", Unit=self.UNITS['Reboot'], TypeName='Push Off').Create()
        
        # Заполняем первоначальные данные 
        if (self.UNITS['Audio'] in Devices):
            self.audioState = Devices[self.UNITS['Audio']].nValue
            
        if (self.UNITS['Volume'] in Devices):
            self.audioVolumeLevel = Devices[self.UNITS['Volume']].nValue
                        
        # Выбираем протокол соединения
        if (Parameters["Port"] == "443"): 
            self.sProtocol = "https"

        Domoticz.Connection(Name="SlsPing", Transport="TCP/IP", Protocol=self.sProtocol, Address=Parameters["Address"], Port=Parameters["Port"]).Connect()

        # Опросим шлюз
        self.status()
        
        # Период обновления
        Domoticz.Heartbeat(30)
        return True
    
    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port)
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
            # Turn devices off in Domoticz
            for Key in Devices:
                UpdateDevice(Key, 0, Devices[Key].sValue)
        return True
    
    # Синхронизируем устройства
    def SyncDevices(self):
        UpdateDevice(self.UNITS['Audio'], self.audioState, self.audioUrl)
        UpdateDevice(self.UNITS['Volume'], self.audioState, ""+str(self.audioVolumeLevel)+"")
    
    # Отправить /api GET запрос на SLS шлюз
    def send(self, payload):
        try:
            url = payload
            # Добавляем токен в запрос (если задан)
            if (Parameters["Password"]):
                sep = '?'
                if payload.find('?') != -1 :
                    sep = '&'
                url = payload+sep+"token="+Parameters["Password"]
            
            Domoticz.Debug("Request - "+str(url))
            req = request.Request(self.sProtocol+'://' + Parameters["Address"] + ':' + Parameters["Port"] + '/api/'+url)
            response = request.urlopen(req, timeout=3).read()
            response = response.decode("utf-8", "ignore")
            Domoticz.Debug('Response - ' + str(response) )
            return json.loads(response)
        except Exception as e:
            Domoticz.Error('Connection error: ' + str(e.reason) )
            return False
        
    def reboot(self):
        # self.send('reboot') # Обещают в следующей версии
        self.send('scripts?action=evalCode&plain=os.restart()')
        
    def audioPlay(self, url):
        self.audioUrl=url
        self.send('audio?action=play&url='+url)
        self.audioStatus()
        self.audioUrlStatus()
        
    def audioStop(self):
        self.send('audio?action=stop')
        self.audioStatus()
        
    def audioVolumeSet(self, level):
        self.send('audio?action=setvolume&value='+str(level))
        self.audioVolumeStatus()
        
    def audioStatus(self):
        result = self.send('audio?action=getstatus')
        if result:
            self.audioState = result['result']
            self.SyncDevices()
        
    def audioVolumeStatus(self):
        result = self.send('audio?action=getvolume')
        if result:
            self.audioVolumeLevel = result['result']
            self.SyncDevices()
        
    def audioUrlStatus(self):
        result = self.send('audio?action=geturl')
        if result:
            self.audioUrl = result['result']
            self.SyncDevices()
        
    def status(self):
        self.audioStatus()
        self.audioVolumeStatus()
        self.audioUrlStatus()
        
    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage "+str(Data)+"")
        self.SyncDevices()
        return True

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level) + "', Hue: " + str(Hue))
        Command = Command.strip()
        
        # Останавливаем аудио
        if (self.UNITS['Audio']==Unit):
            self.audioStop()
            
        # Меняем громкость
        if (self.UNITS['Volume']==Unit):
            if (Command=='Off'): #"Set Level"
                Level = 0
            self.audioVolumeSet(Level)
        
        # Перезагружаем SLS
        if (self.UNITS['Reboot']==Unit):
            self.reboot()
            
        return True

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)


    def onHeartbeat(self):
        self.status()
        return True

    def onDisconnect(self, Connection):
        Domoticz.Log("Device has disconnected")
        return

    def onStop(self):
        Domoticz.Log("onStop called")
        return True

    def ClearDevices(self):
        # Stop everything and make sure things are synced
        self.audioState = 1
        self.audioUrl = ""

        self.SyncDevices()
        return
        
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image:     " + str(Devices[x].Image))
    return
 
def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return
