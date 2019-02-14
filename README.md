# Tasmota Device Manager
GUI application to discover and monitor devices flashed with [Tasmota firmware](https://github.com/arendst/Sonoff-Tasmota)

![image.png](https://github.com/jziolkowski/tdm/blob/master/image.png)

# Features

 - autodetection of devices following the default topic template for Tasmota (%prefix%/%topic%/) and for HomeAssistant Auto Discovery protocol (%topic%/%prefix%/)
 - devices with different syntax can be added manually.
 - passive monitoring of state and telemetry (currently supported sensors are listed in "status8.json")
 - clean, readable interface
 - relay control via context menu on device list (all ON/OFF, or individual)
 - clean retained relay topic messages.
 - MQTT console with payload preview (dbl-click an entry to display), sorting and filtering.
 - selectable detail columns in device list
 - BSSID aliasing for larger deployments

# Planned functions
 
 - active querying of state and telemetry (with configurable list of queried statuses)
 - dynamic and manual grouping of devices: by group topic, module, firmware revision, and more
 - group actions: reset/restart/control power/upgrade
 - console commands with topic and syntax completion
 - module and GPIO configuration
 - easy access to advanced settings and commands from Tastmota
 - quick settings for common use cases
 - rules editor
 - customizable order of detail columns in device list
 - and much more! (you're welcome to post feature requests)

# Requirements

Python 3.4+

PyQt5: <pre>pip install PyQt5</pre>
paho-mqtt: <pre>pip install paho-mqtt</pre>

Uses free icons from [FatCow](https://www.fatcow.com/free-icons)
