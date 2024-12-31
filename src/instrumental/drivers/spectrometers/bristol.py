# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nikolas Tezak, Nate Bogdanowicz
"""
Driver for Bristol 721 spectrum analyzers.
"""
import os
import sys
from contextlib import contextmanager
from functools import wraps
import ctypes
import numpy as np
from numpy.ctypeslib import ndpointer

from . import Spectrometer
from .. import ParamSet
from ... import u

_INST_PARAMS = ['port']
_INST_CLASSES = ['Bristol_721']

bristol_dll = ctypes.WinDLL("BristolFFT.dll", use_errno=True, use_last_error=True)
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

bristol_dll.CLGetPowerReading.argtypes = [ctypes.c_int]
bristol_dll.CLGetPowerReading.restype = ctypes.c_float

bristol_lv_dll.CLGetNextSpectrum.argtypes = [
    ctypes.c_int,
    ndpointer(np.float32, ndim=1, flags='C_CONTIGUOUS'),
    ndpointer(np.float32, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_int
]


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


class Bristol_721(Spectrometer):
    def _initialize(self):
        self._com_port = self._paramset.get('port') or find_comm_port()
        self._dll = bristol_dll
        self._lv = bristol_lv_dll
        self._handle = open_device(self._com_port)

        if self._handle < 0:
            raise Exception("Failed to open connection to spectrum analyzer")
        elif self._handle == 0:
            raise Exception("You must have already opened the port")

        self._lv.CLRegister(self._handle)

        # Hard-coded for now, ideally we'd auto-detect this via a model byte or something
        self._model = 'IR'
        self._range_num = 0

    def _fft_range(self):
        fft_size, dec, fold, low_wav, hi_wav = FFT_INFO[(self._model, self._range_num)]
        low_index = bin_index(fft_size, dec, fold, low_wav)
        high_index = bin_index(fft_size, dec, fold, hi_wav)
        if low_index > high_index:
            low_index, high_index = high_index, low_index
        return int(low_index+1), int(high_index-1)  # Exclude edge of the range to be safe

    def get_wavelength(self):
        """Get the vacuum wavelength of the tallest peak in the spectrum

        Returns
        -------
        wavelength : Quantity
            The peak wavelength, in nm
        """
        return self._dll.CLGetLambdaReading(self._handle) * u.nm

    def get_spectrum(self):
        """Get a spectrum.

        Returns
        -------
        x : array Quantity
            Wavelength of the bins, in nm
        y : array
            Power in each bin, in arbitrary units
        """
        start, stop = self._fft_range()
        size = stop-start
        self._dll.CLGetFullSpectrum(self._handle, start, stop)

        wavenumber = np.zeros(size, np.float32)
        power = np.zeros(size, np.float32)

        ret = 0
        while not ret:
            ret = self._lv.CLGetNextSpectrum(self._handle, power, wavenumber, size)

        # For some reason, x is not sorted already...
        indices = np.argsort(wavenumber)
        return 1e10/wavenumber[indices] * u.nm, power[indices]  # Is this scaling right?

    def close(self):
        self._dll.CLCloseDevice(self._handle)


def list_instruments():
    com_ports = [find_comm_port()]  # TODO: Add support for multiple connected devices
    return [ParamSet(Bristol_721, port=port) for port in com_ports]
