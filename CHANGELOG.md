## [2024.9.3]
## Added
- up to 8 shutters supported

## Changed
- ethernet-enabled devices now show eth ip address when wifi is disabled (#266)
- rows in device list are slimmer now
- made shutter icons in device list smaller

## Fixed
- clicking main menu buttons doesn't crash anymore (#235)

## [2024.9.2] - 2024-09-14
## Fixed
- missing pydantic in pyproject.toml

## [2024.9.1] - 2024-09-12
## Changed
- semver -> calver, because following major/minor etc would not necessarily follow Tasmota features/breaking changes
- TDM now stores tdm.cfg in locations suggested by the OS

## Added
- support for MQTT wildcards in autodiscovery patterns (#254)
- misc UI changes

## Fixed
- many bugs, crashes, small annoyances

## [0.2.6] - 2019-12-24
## Changed
- support for 16 var/mem in rules editor
- for older devices, the missing rows now say "unknown" instead of "loading" to avoid confusion

## [0.2.5] - 2019-12-06
### Added
- now available as `tdmgr.exe` for Windows
- now available on PyPI as `tdmgr`
- support for SetOption4 (commands reply on /<COMMAND> topic instead of /RESULT)

## Changed
- removed support for Var/Mem command JSON payload for Tasmota pre 6.6.0.12
- rule parser now doesn't throw errors when rule contains JSON

## [0.2.4] - 2019-12-04
### Added
- optional MQTT messages dump for devices

## Changed
- main script name changed to `tdmgr.py` prior to packaging on PyPI (due to conflicting name with other project)

## [0.2.3] - 2019-11-27
### Added
- ~/TDM directory is created automatically if missing, to prevent logging module crash

### Fixed
- forced RSSI to be cast as int() for some odd cases
- reconnect is now enough to subscribe to new custom patterns (thanks to pgollor)

## [0.2.2] - 2019-11-21
### Added
- Device list now sorts correctly when using diactrics in friendly names
- Some logging features for MQTT and Autodiscovery process
- Toolbar actions now available in device list context menu (#55)
- Preferences dialog: console word-wrap setting and font size and version formatting option for device list
- Clear obsolete LWTs dialog added in MQTT menu
- Save/Clear functions to console

### Fixed
- Power ALL was sending true/false instead of 0/1 (#53)

## [0.2.1] - 2019-11-16
### Fixed
- forced sorting of POWER\<x\> keys when generating toggle actions and drawing state icons
- exception catching when SetOption parsing fails in older Tasmota versions

## [0.2.0] - 2019-10-02
### Added
- consoles for each device, with colored output to ease reading (needs some polishing), command completion and history
- buttons, switches and relays configuration dialog
- custom widgets in the redesigned device list, including different views

### Changed
- most of the codebase rewritten
