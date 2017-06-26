# -*- coding: utf-8 -*-
# Copyright 2014-2016 Nate Bogdanowicz

try:
    import configparser  # Python 3
except ImportError:
    import ConfigParser as configparser  # Python 2

import sys
import os.path
from warnings import warn
from ast import literal_eval
from . import appdirs

__all__ = ['servers', 'instruments', 'prefs']
servers, instruments, prefs = {}, {}, {}
user_conf_dir = appdirs.user_data_dir("Instrumental", "MabuchiLab")

pkg_dir = os.path.abspath(os.path.dirname(__file__))
user_conf_path = os.path.join(user_conf_dir, 'instrumental.conf')
pkg_conf_path = os.path.join(pkg_dir, 'instrumental.conf.default')


def copy_file_text(from_path, to_path):
    """Copies a text file, using platform-specific line endings"""
    with open(from_path, 'rU') as from_file:
        with open(to_path, 'w') as to_file:
            to_file.writelines((line for line in from_file))


def install_default_conf():
    try:
        os.makedirs(user_conf_dir)
    except OSError:
        pass  # Data directory already exists
    copy_file_text(pkg_conf_path, user_conf_path)


def load_config_file():
    global servers, instruments, prefs # Not strictly necessary, but suggestive
    parser = configparser.RawConfigParser()
    parser.optionxform = str  # Re-enable case sensitivity

    if not os.path.isfile(user_conf_path):
        install_default_conf()
    parser.read(user_conf_path)

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

    if 'data_directory' in prefs:
        prefs['data_directory'] = os.path.normpath(os.path.expanduser(prefs['data_directory']))

    blacklist = prefs.setdefault('driver_blacklist', [])
    if blacklist:
        prefs['driver_blacklist'] = [entry.strip() for entry in blacklist.split(',')]


# Run on import
load_config_file()
