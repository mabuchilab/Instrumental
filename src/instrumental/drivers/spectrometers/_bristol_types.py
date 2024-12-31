# -*- coding: utf-8 -*-
# Copyright 2014-2015 Nikolas Tezak, Nate Bogdanowicz
"""Module that contains structs, typedefs, and other odds-and-ends from the Bristol header files"""

from ctypes import (Structure, c_ubyte, c_ulong, c_char, c_short, c_long, c_ushort, c_float,
                    c_double, CFUNCTYPE, POINTER)

# Define basic types
BYTE = c_ubyte
DWORD = c_ulong
WORD = c_ulong

# from pctypes.h
SBYTE = c_char
SWORD = c_short
SDWORD = c_long
UBYTE = c_ubyte
UWORD = c_ushort
UDWORD = c_ulong


# Define Structs
RAW_DATA_MAX = 1024
DISPLAY_FFT_SIZE = 512


class header_type(Structure):
    _fields_ = [('id', BYTE),
                ('seq_no', BYTE),
                ('cksum', UWORD),
                ('length', WORD),
                ('unused', WORD)]


class tsMeasurementDataType(Structure):
    _fields_ = [('ScanIndex', DWORD),
                ('Status', DWORD),
                ('Temperature', c_float),
                ('Pressure', c_float),
                ('RefPower', DWORD),
                ('InputPower', c_float),
                ('Wavelength', c_double),
                ('Decimation', DWORD),
                ('Fold', DWORD),
                ('FFTSize', DWORD),
                ('SpectrumStart', SWORD),
                ('SpectrumEnd', SWORD),
                ('RefLambda', c_double),
                ('Reserved', DWORD*8)]


class tsConfigParam(Structure):
    _fields_ = [('mnAverages', DWORD),
                ('meAverageEnable', BYTE),
                ('mePowerUnits', BYTE),
                ('meWavelengthUnits', BYTE),
                ('meGainState', BYTE),
                ('meMedium', BYTE),
                ('meMeasurementMode', BYTE),
                ('meAutoResolutionEnable', BYTE),
                ('meWindowType', BYTE)]


class tsSpecDataType(Structure):
    _fields_ = [('ScanIndex', DWORD),
                ('mnDataPoints', DWORD),
                ('mnStartBin', DWORD),
                ('mfSpectrumStart', c_float),
                ('mfSpectrumEnd', c_float),
                ('maSpectrum', c_float*DISPLAY_FFT_SIZE)]


class tsCoAddDataType(Structure):
    _fields_ = [('mbLeftNotRight', DWORD),
                ('maFifoData', DWORD*10),
                ('mnCenterWidth', DWORD)]


class set_value_msg_type(Structure):
    _fields_ = [('header', header_type),
                ('value', SDWORD)]


class tsFullSpectrumDataMsgType(Structure):
    _fields_ = [('header', header_type),
                ('DataType', SWORD),
                ('Status', SWORD),
                ('PacketNumber', SWORD),
                ('TotalPackets', SWORD),
                ('SpectrumStartIndex', DWORD),
                ('SpectrumEndIndex', DWORD),
                ('NPoints', DWORD),
                ('Data', UWORD*RAW_DATA_MAX)]


# Define callback signatures
FULLSPECTRUMCALLBACK = CFUNCTYPE(None, POINTER(tsFullSpectrumDataMsgType))
