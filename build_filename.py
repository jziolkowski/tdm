import os
import re


def get_version():
    with open("tdmgr.py", "r") as tdmgr:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", tdmgr.read(), re.M)
        return version_match.group(1)
