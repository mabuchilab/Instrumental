# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import declspec_hook

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES(X86)}\Digital Camera Toolbox\Pixelfly SDK\include",
            r"{PROGRAMFILES}\Digital Camera Toolbox\Pixelfly SDK\include",
        ),
        'header': ('PfcamExport.h', 'pccamdef.h'),
    },
}

lib_names = {'win*': 'pf_cam'}


def build():
    build_lib(header_info, lib_names, '_pixelflylib', __file__, token_hooks=(declspec_hook,))


if __name__ == '__main__':
    import logging as log
    log.basicConfig(level=log.DEBUG)
    build()
