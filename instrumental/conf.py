# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz

try:
    import configparser # Python 3
except ImportError:
    import ConfigParser as configparser # Python 2

import sys
import os.path
from .appdirs import user_data_dir

__all__ = ['servers', 'instruments', 'prefs']
servers, instruments, prefs = {}, {}, {}

# Load user config file
data_dir = user_data_dir("Instrumental", "MabuchiLab")
parser = configparser.RawConfigParser()
parser.optionxform = str # Re-enable case sensitivity
parser.read(os.path.join(data_dir, 'instrumental.conf'))

# Write settings into this module's __dict__
this_module = sys.modules[__name__]
for section_str in parser.sections():
    section = {}
    safe_section_str = section_str.replace(" ", "_")
    # Make each section an attribute of this module
    setattr(this_module, safe_section_str, section)
    for key, value in parser.items(section_str):
        section[key] = value

try:
    def_serv = prefs['default_server']
    if def_serv in servers.keys():
        prefs['default_server'] = servers[def_serv]
except KeyError:
    # 'prefs' or 'servers' sections empty or nonexistent
    pass
