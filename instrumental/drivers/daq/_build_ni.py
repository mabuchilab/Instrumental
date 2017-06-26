# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
from nicelib import build_lib

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES(X86)}\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include",
            r"{PROGRAMFILES}\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include",
        ),
        'header': 'NIDAQmx.h'
    },
    'linux*': {
        'path': '/usr/local/natinst/nidaqmx/include',
        'header': 'NIDAQmx.h'
    },
    'darwin*': {
        'path': '/Applications/National Instruments/NI-DAQmx Base/includes',
        'header': 'NIDAQmxBase.h'
    },
}

lib_names = {'win*': 'nicaiu', 'linux*': 'nidaqmx', 'darwin*': 'nidaqmxbase'}


def build():
    build_lib(header_info, lib_names, '_nilib', __file__)


if __name__ == '__main__':
    build()
