import os
import re
from setuptools import setup

with open("README.md", "r") as rme:
    readme = rme.read()

with open("CHANGELOG.md", "r") as clog:
    changelog = clog.read()

long_description = "{}\n\n# Changelog\n{}".format(readme, changelog)

if os.name == "nt":
    scripts = None
    entry_points = {
        {
        'console_scripts': ['cwiotmgr=cwiotmgr:main'],
        }
    }
else:
    scripts = ['cwiotmgr.py']
    entry_points = None

def get_version():
    with open("cwiotmgr.py", "r") as tdmgr:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  tdmgr.read(), re.M)
        return version_match.group(1)

setup(
    name='cwiotmgr',
    version=get_version(),
    url='https://github.com/jziolkowski/tdm',
    license='GPLv3',
    author='Stephen Harris',
    author_email='stephen.harris@cricketwireless.com',
    description='Cricket Wireless IOT Device Manager is able to find, monitor and do magic things with IOT devices. The easy way. Like a Superhero.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.6',
    install_requires=[
        "paho_mqtt>=1.4",
        "PyQt5>=5.12"
    ],
    packages=['GUI', 'Util'],
    entry_points=entry_points,
    scripts=scripts,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
        "Development Status :: 4 - Beta"
    ],
    project_urls={
        "Issue Tracker": "https://github.com/jziolkowski/tdm/issues",
        "Documentation": "https://github.com/jziolkowski/tdm/wiki",
    },
)
