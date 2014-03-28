# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz

import os
import os.path
import shutil

from setup import name, author
from instrumental.appdirs import user_data_dir

data_dir = user_data_dir(name, author)
conf_filename = 'instrumental.conf'
user_conf_path = os.path.join(data_dir, conf_filename)
default_conf_path = os.path.join('data', conf_filename)

try:
    os.makedirs(data_dir)
except OSError as e:
    pass # Dir already exists

# Only copy default config file if user doesn't have one already
if not os.path.isfile(user_conf_path):
    shutil.copyfile(default_conf_path, user_conf_path)
