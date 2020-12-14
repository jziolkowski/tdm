# Tasmota Device Manager
Easy to use GUI application to manage, configure and monitor devices flashed with [Tasmota firmware](https://github.com/arendst/Tasmota)

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/jziolkowski/tdm?style=for-the-badge)](https://github.com/jziolkowski/tdm/releases/latest)
[![GitHub All Releases](https://img.shields.io/github/downloads/jziolkowski/tdm/total?logo=github&style=for-the-badge)](https://github.com/jziolkowski/tdm/releases/latest)
[![https://pypi.org/project/tdmgr/](https://img.shields.io/pypi/dw/tdmgr?logo=pypi&style=for-the-badge)](https://pypi.org/project/tdmgr/)
[![Discord](https://img.shields.io/discord/545967340794413078?logo=discord&style=for-the-badge)](https://discord.gg/eAhVDXM)
[![https://www.buymeacoffee.com/eYmkLXO](https://img.shields.io/badge/Donate-Buy%20me%20a%20coffee-orange?style=for-the-badge)](https://www.buymeacoffee.com/eYmkLXO)

![image](https://user-images.githubusercontent.com/11555742/66050573-bf764900-e52d-11e9-8356-e3dbf4ef6205.png)

#### Minimum fully-supported Tasmota firmware version: [6.6.0.17](https://github.com/arendst/Tasmota/blob/development/tasmota/CHANGELOG.md#66017-20191009)

#### To the users:
I'm very grateful for all your support over the months, ideas, and donations, and most of all: patience.
While I'm not in any way abandoning this project, I don't have as much time as I'd like to work on it. If anything, keep being patient as new features will come, but I'm not at liberty of setting any deadlines or plans.


# Features

 - [autodiscovery](https://github.com/jziolkowski/tdm/wiki/Autodiscovery) of Tasmota devices (even if they use custom FullTopics)
 - module, GPIO and template configuration
 - rules editor with Var/Mem/Ruletimer monitor
 - easy to read detachable telemetry viewers (working in active and passive mode) 
 - relay, color and PWM control
 - user-friendly configuration of buttons, switches and relays, including their related SetOptions
 - timers editor
 - clear retained relay and LWT topics
 - detachable device consoles with command completion and intuitive history 
 - selectable views to see the most vital device parameters at a glance
 - BSSID aliasing for larger deployments
 - support for current and legacy Timers payloads (thanks @GrahamM)

# Planned functions
  
 - PWM/NTP/Topics configuration dialogs and a few others
 - config export for OpenHAB and HomeAssistant
 - dynamic and manual grouping of devices: by group topic, module, firmware revision, and more
 - group actions: reset/restart/control power/upgrade
 - quick settings for common use cases
 - code completion in rules editor
 - built-in OTA server
 - and much more! (you're welcome to post feature requests)

# Requirements and installation instructions

See the [wiki article](https://github.com/jziolkowski/tdm/wiki/Prerequisites-installation-and-running)

Uses free icons from [Icons8](https://icons8.com)

Kind thanks to all users that report issues and provide PRs!
