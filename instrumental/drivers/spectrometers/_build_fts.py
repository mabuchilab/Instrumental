# -*- coding: utf-8 -*-
"""
Copyright 2016 Christopher Rogers
"""

from nicelib import build_lib

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES}\Thorlabs\Thorlabs OSA\include",
            r"{PROGRAMFILES(X86)}\Thorlabs\Thorlabs OSA\include",
        ),
        'header': 'FTS.h'
    },
}

lib_names = {'win*': 'FTSLib.dll'}


def build():
    build_lib(header_info, lib_names, '_ftslib', __file__)
    
"""
def vi_func_hook(tokens):
    "Removes _VI_FUNC from return_value _VI_FUNC function (args)"
    return modify_pattern(tokens, [('d', '__fastcall'),])

def build():
    build_lib(header_info, lib_names, '_tlccslib', __file__, token_hooks=(vi_func_hook,))
"""
