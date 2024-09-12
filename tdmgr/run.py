#!/usr/bin/env python
import argparse
import logging
import os
import pathlib
import sys

from PyQt5.QtCore import QDir, QSettings
from PyQt5.QtWidgets import QApplication

from tdmgr.GUI import icons  # noqa: F401
from tdmgr.GUI.dialogs.main import MainWindow

try:
    from tdmgr._version import version
except ImportError:
    version = ""


def get_settings(args):
    if args.local:
        return QSettings("tdm.cfg", QSettings.IniFormat)
    if args.config_location:
        return QSettings(os.path.join(args.config_location, "tdm.cfg"), QSettings.IniFormat)
    return QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "tdm")


def get_devices(args):
    if args.local:
        return QSettings("devices.cfg", QSettings.IniFormat)
    if args.config_location:
        return QSettings(os.path.join(args.config_location, "devices.cfg"), QSettings.IniFormat)
    return QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", "devices")


def get_log_path(args):
    if args.local:
        return "tdm.log"
    if args.log_location:
        return os.path.join(args.log_location, "tdm.log")
    return os.path.join(QDir.tempPath(), "tdm.log")


def setup_parser():
    parser = argparse.ArgumentParser(prog='Tasmota Device Manager')
    parser.add_argument('--debug', action='store_true', help='Enable debugging')
    parser.add_argument(
        '--local',
        action='store_true',
        help='Store configuration and logs in the directory where TDM was started',
    )
    parser.add_argument('--config-location', type=pathlib.Path)
    parser.add_argument('--log-location', type=pathlib.Path)
    return parser


def start():
    parser = setup_parser()
    args = parser.parse_args()

    try:
        app = QApplication(sys.argv)
        app.lastWindowClosed.connect(app.quit)
        app.setStyle("Fusion")

        settings, devices, log_path = get_settings(args), get_devices(args), get_log_path(args)
        MW = MainWindow(version, settings, devices, log_path, args.debug)
        MW.show()
        sys.exit(app.exec_())

    except Exception as e:  # noqa: 722
        logging.exception("EXCEPTION: %s", e)
        print(
            f"TDM has crashed. Sorry for that. Check {os.path.join(QDir.tempPath(), 'tdm.log')} "
            f"for more information."
        )


if __name__ == "__main__":
    start()
