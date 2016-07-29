# -*- coding: utf-8 -*-
"""
Copyright 2016 Christopher Rogers
"""
import platform
from nicelib import build_lib
from nicelib.process import modify_pattern

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES}\IVI Foundation\VISA\Win64\Include",
            r"{PROGRAMFILES(X86)}\IVI Foundation\VISA\Win64\Include"
        ),
        'header': 'TLCCS.h'
    },
}

if platform.architecture()[0] == '64bit':
    lib_names = {'win*': 'TLCCS_64.dll'}
else:
    lib_names = {'win*': 'TLCCS_32.dll'}


def vi_func_hook(tokens):
    """Removes __fastcall references (which show up as _VI_FUNC)"""
    return modify_pattern(tokens, [('d', '__fastcall'),])

def build():
        build_lib(header_info, lib_names, '_tlccslib', __file__, token_hooks=(vi_func_hook,))
