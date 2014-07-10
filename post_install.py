# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz

import os
import os.path
import sys
from setup import name, author
from instrumental.appdirs import user_data_dir


def copy_file_text(from_path, to_path):
    """Copies a text file, using platform-specific line endings"""
    with open(from_path, 'rU') as from_file:
        with open(to_path, 'w') as to_file:
            to_file.writelines((line for line in from_file))


data_dir = user_data_dir(name, author)
conf_filename = 'instrumental.conf'
user_conf_path = os.path.join(data_dir, conf_filename)
default_conf_path = os.path.join('data', conf_filename)

try:
    os.makedirs(data_dir)
except OSError as e:
    pass  # Dir already exists

force = (len(sys.argv) > 1 and sys.argv[1] == '--force')
file_exists = os.path.isfile(user_conf_path)

if force or not file_exists:
    if file_exists:
        print("Forcing overwrite of existing config file...")

    copy_file_text(default_conf_path, user_conf_path)
    print("Wrote config file to '{}'".format(user_conf_path))
else:
    print("Config file '{}' already exists.\n\n".format(user_conf_path) +
          "Use `{} --force` to force overwrite.".format(sys.argv[0]))
