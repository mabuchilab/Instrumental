# -*- coding: utf-8 -*-
# Copyright 2014-2015 Nate Bogdanowicz

try:
    import configparser  # Python 3
except ImportError:
    import ConfigParser as configparser  # Python 2

import sys
import os.path
from warnings import warn
from ast import literal_eval
from .appdirs import user_data_dir

__all__ = ['servers', 'instruments', 'prefs']
servers, instruments, prefs = {}, {}, {}
data_dir = user_data_dir("Instrumental", "MabuchiLab")


def load_config_file():
    global servers, instruments, prefs # Not strictly necessary, but suggestive
    parser = configparser.RawConfigParser()
    parser.optionxform = str  # Re-enable case sensitivity
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

    # Parse 'instruments' section's values as dicts
    for key, value in instruments.items():
        bad_value = False
        try:
            d = literal_eval(value)
        except ValueError:
            bad_value = True

        if bad_value or not isinstance(d, dict):
            warn("Bad value for key `{}` in instrumental.conf. ".format(key) +
                 "Values `instruments` section of instrumental.conf " +
                 "must be written as python-style dictionaries. Remember to " +
                 "enclose keys and values in quotes.")
            d.pop(key)
        else:
            instruments[key] = d

    try:
        def_serv = prefs['default_server']
        if def_serv in servers.keys():
            prefs['default_server'] = servers[def_serv]
    except KeyError:
        # 'prefs' or 'servers' sections empty or nonexistent
        pass

    if 'data_directory' in prefs:
        prefs['data_directory'] = os.path.expanduser(prefs['data_directory'])


# Run on import
load_config_file()
