# -*- coding: utf-8 -*-
"""
Copyright 2016 Christopher Rogers
"""
from nicelib import build_lib

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES}\Princeton Instruments\PICam\Includes",
        ),
        'header': 'picam.h'
    },
}

# lib_names = {'win*': r"{PROGRAMFILES}\Princeton Instruments\PICam\Runtime\Picam.dll",}
lib_names = {'win*': r"Picam.dll",}

def build():
        build_lib(header_info, lib_names, '_picamlib', __file__,
                  hook_groups=('C++'))

"""
fname = 'wrapper.py'
f = open(fname, 'w+')
generate_wrapper(header_info, f, hook_groups=('C++'), prefix=('Picam_',))
f.close()
"""
