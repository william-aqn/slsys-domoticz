# SLS gateway Domoticz plugin
![Settings](/assets/devices.png)

# Installation

* Make sure your Domoticz instance supports Domoticz Plugin System - see more https://domoticz.com/wiki/Using_Python_plugins

* Get plugin data into DOMOTICZ/plugins directory
```
cd YOUR_DOMOTICZ_PATH/plugins
git clone https://github.com/william-aqn/slsys-domoticz
```
Restart Domoticz
* Go to Setup > Hardware and create new Hardware with type: **SLS gateway**
* Enter name (it's up to you), ip, port and token if define.
* Fill radio urls separated `|` symbol
![Settings](/assets/settings.png)

## Update
```
cd YOUR_DOMOTICZ_PATH/plugins/slsys-domoticz
git pull
```
* Restart Domoticz
