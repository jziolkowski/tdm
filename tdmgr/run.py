#!/usr/bin/env python
import argparse
import logging
import os
import pathlib
import sys
from logging.handlers import TimedRotatingFileHandler

from PyQt5.QtCore import QDir, QSettings
from PyQt5.QtWidgets import QApplication

from tdmgr.GUI import icons  # noqa: F401
from tdmgr.GUI.dialogs.main import MainWindow

try:
    from tdmgr._version import version
except ImportError:
    version = ""


def configure_logging(args) -> None:
    log_path = os.path.join(QDir.tempPath(), "tdm.log")

    if args.local:
        log_path = "tdm.log"
    elif args.log_location:
        log_path = os.path.join(args.log_location, "tdm.log")

    logging.basicConfig(
        level="DEBUG" if args.debug else "INFO",
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s [%(levelname)s] [%(filename)s] %(message)s",
    )

    logging.getLogger().addHandler(
        TimedRotatingFileHandler(filename=log_path, when="d", interval=1)
    )


def get_settings(args: argparse.Namespace, filename: str) -> QSettings:
    if args.local:
        return QSettings(filename, QSettings.IniFormat)
    if args.config_location:
        return QSettings(os.path.join(args.config_location, filename), QSettings.IniFormat)
    return QSettings(QSettings.IniFormat, QSettings.UserScope, "tdm", filename)


def setup_parser() -> argparse.ArgumentParser:
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


def start() -> None:
    parser = setup_parser()
    args = parser.parse_args()
    configure_logging(args)

    try:
        app = QApplication(sys.argv)
        app.lastWindowClosed.connect(app.quit)
        app.setStyle("Fusion")

        settings, devices = get_settings(args, "tdm"), get_settings(args, "devices")
        MW = MainWindow(version, settings, devices, args.debug)
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
