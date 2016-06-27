# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
from instrumental.drivers.build_ffi_lib import build_lib

header_paths = {
    'win*': (
        r"{PROGRAMFILES(X86)}\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h",
        r"{PROGRAMFILES}\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h",
    ),
    'linux*': (
        "/usr/local/natinst/nidaqmx/include/NIDAQmx.h",
    ),
    'darwin*': (
        "/Applications/National Instruments/NI-DAQmx Base/includes/NIDAQmxBase.h",
    ),
}

lib_names = {'win*': 'nicaiu', 'linux*': 'nidaqmx', 'darwin*': 'nidaqmxbase'}


def build():
    build_lib(header_paths, lib_names, '_nilib')


if __name__ == '__main__':
    build()
