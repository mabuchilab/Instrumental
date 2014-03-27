# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

try:
    import configparser # Python 3
except ImportError:
    import ConfigParser as configparser # Python 2

import os.path
from appdirs import user_data_dir
from pint import UnitRegistry

# Load user config file
data_dir = user_data_dir("Instrumental", "MabuchiLab")
parser = configparser.RawConfigParser()
parser.optionxform = str # Re-enable case sensitivity
parser.read(os.path.join(data_dir, 'instrumental.conf'))

settings = {}
for section_str in parser.sections():
    section = {}
    settings[section_str] = section
    for key, value in parser.items(section_str):
        section[key] = value

try:
    def_serv = settings['prefs']['default_server']
    if def_serv in settings['servers'].keys():
        settings['prefs']['default_server'] = settings['servers'][def_serv]
except KeyError:
    # No section named 'prefs' or 'servers'
    pass

# Make a single UnitRegistry instance for the entire package
u = UnitRegistry()
Q_ = u.Quantity

# Make common functions available directly
from .plotting import plot, param_plot
from .fitting import guided_trace_fit, guided_ringdown_fit
from .drivers import instrument
from .drivers.scopes import scope, SCOPE_A, SCOPE_B
from .tools import fit_scan, fit_ringdown
