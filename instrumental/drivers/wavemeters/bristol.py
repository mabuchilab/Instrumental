# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nikolas Tezak, Nate Bogdanowicz
"""
Driver for Bristol 621 wavemeters.
"""
import os
import sys
from contextlib import contextmanager
from functools import wraps
import ctypes
import numpy as np
from numpy.ctypeslib import ndpointer

from . import Wavemeter
from .. import ParamSet
from ... import u

_INST_PARAMS = ['port']
_INST_CLASSES = ['Bristol621']

bristol_dll = ctypes.CDLL("CLDevIface.dll", use_errno=True, use_last_error=True)
bristol_lv_dll = ctypes.WinDLL("BristolLV.dll", use_errno=True, use_last_error=True)


# Set DLL function signatures
find_comm_port = bristol_lv_dll.CLFindBristolCommPort
find_comm_port.restype = ctypes.c_int

open_device = bristol_dll.CLOpenUSBSerialDevice
open_device.argtypes = [ctypes.c_int]
open_device.restype = ctypes.c_int

get_lambda = bristol_dll.CLGetLambdaReading
get_lambda.argtypes = [ctypes.c_int]
get_lambda.restype = ctypes.c_double

get_power = bristol_dll.CLGetPowerReading
get_power.argtypes = [ctypes.c_int]
get_power.restype = ctypes.c_float

close_device = bristol_dll.CLCloseDevice
close_device.argtypes = [ctypes.c_int]
close_device.restype = ctypes.c_int

# Adapted from <http://stackoverflow.com/a/17954769>
@contextmanager
def stderr_redirected(to=os.devnull):
    fd = sys.stderr.fileno()

    def _redirect_stderr(to):
        sys.stderr.close()
        os.dup2(to.fileno(), fd)
        sys.stderr = os.fdopen(fd, 'w')

    with os.fdopen(os.dup(fd), 'w') as old_stderr:
        with open(to, 'w') as file:
            _redirect_stderr(to=file)
        try:
            yield
        finally:
            _redirect_stderr(to=old_stderr)


# Decorator for redirecting stderr to /dev/null for the function's duration
def ignore_stderr(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with stderr_redirected():
            return f(*args, **kwargs)
    return wrapper


# Table obtained from Bristol technical support
FFT_INFO = {
    ('VIS', 0): (131072, 1, 3, 350, 421),
    ('VIS', 1): (131072, 1, 2, 423, 632),
    ('VIS', 2): (131072, 1, 1, 632, 1100),
    ('NIR', 0): (131072, 1, 2, 500, 632),
    ('NIR', 1): (131072, 1, 1, 633, 1265),
    ('NIR', 2): (32768,  4, 3, 1266, 1685),
    ('IR',  0): (65536,  1, 0, 1266, 5000),
    ('MIR', 0): (32768,  5, 1, 4000, 6329),
    ('MIR', 1): (16384,  9, 1, 5700, 11000),
    ('XIR', 0): (131072, 1, 0, 1500, 12000),
}


def bin_index(fft_size, dec, fold, lamb):
    if fold % 2 == 0:
        bin = ((2*dec*632.9914)/lamb - fold) * fft_size
    else:
        bin = (fold + 1 - (2*dec*632.9914)/lamb) * fft_size
    return bin


class Bristol621(Wavemeter):
    def _initialize(self):
        self._com_port = self._paramset.get('port') or find_comm_port()
        self._dll = bristol_dll
        self._handle = open_device(self._com_port)

        if self._handle < 0:
            raise Exception("Failed to open connection to spectrum analyzer")
        elif self._handle == 0:
            raise Exception("You must have already opened the port")

        # Hard-coded for now, ideally we'd auto-detect this via a model byte or something
        self._model = 'IR'
        self._range_num = 0


    def get_wavelength(self):
        """Get the vacuum wavelength

        Returns
        -------
        wavelength : Quantity
            The peak wavelength, in nm
        """
        return get_lambda(self._handle) * u.nm

    def get_power(self):
        """Get the power

        Returns
        -------
        power : Quantity
            input power, in mW
        """
        return get_power(self._handle) * u.mW


    def close(self):
        close_device(self._handle)


def list_instruments():
    com_ports = [find_comm_port()]  # TODO: Add support for multiple connected devices
    return [ParamSet(Bristol621, port=port) for port in com_ports]
