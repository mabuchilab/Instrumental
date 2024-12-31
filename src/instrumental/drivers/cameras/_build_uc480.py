# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import declspec_hook

header_info = {
    'win*': (
        {
            'path': (
                r"{PROGRAMFILES(X86)}\Thorlabs\DCx Cameras\Develop\include",
                r"{PROGRAMFILES}\Thorlabs\DCx Cameras\Develop\include",
                r"{PROGRAMFILES(X86)}\Thorlabs\Scientific Imaging\DCx Camera Support\Develop\Include",
                r"{PROGRAMFILES}\Thorlabs\Scientific Imaging\DCx Camera Support\Develop\Include",
            ),
            'header': 'uc480.h'
        },
        {
            'path': (
                r"{PROGRAMFILES(X86)}\IDS\uEye\Develop\include",
                r"{PROGRAMFILES}\IDS\uEye\Develop\include",
            ),
            'header': 'uEye.h'
        }
    ),
}

lib_names = {
    'win*:32': ('uc480', 'ueye_api'),
    'win*:64': ('uc480_64', 'ueye_api_64'),
}


def build():
    build_lib(header_info, lib_names, '_uc480lib', __file__, token_hooks=(declspec_hook,),
              ignore_system_headers=True)


if __name__ == '__main__':
    import logging as log
    log.basicConfig(level=log.DEBUG)
    build()
