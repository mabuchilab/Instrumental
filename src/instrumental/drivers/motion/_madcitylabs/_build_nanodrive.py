# -*- coding: utf-8 -*-
"""
Created the 03/03/2022

@author: Sebastien Weber
"""

from nicelib import build_lib, generate_bindings
from nicelib.process import declspec_hook

header_info = {
    'win*': {
        'path': (
            r"C:\Program Files\Mad City Labs\NanoDrive",
            r"C:\Program Files (x86)\Mad City Labs\NanoDrive",
        ),
        'header': 'Madlib.h'
    },
}

lib_names = {'win*': 'Madlib'}


def build():
    build_lib(header_info, lib_names, '_nanodrivelib', __file__, token_hooks=(declspec_hook,))


def bindings():
    with open('bindings.py', 'w') as f:
        generate_bindings(header_info, f)


if __name__ == '__main__':
    build()
    #bindings()