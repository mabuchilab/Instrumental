# -*- coding: utf-8 -*-
# Copyright 2018 Nate Bogdanowicz
"""
Driver module for Agilent MXG signal generators. Initially developed for and tested onthe N5181A.
"""
from enum import Enum
from . import FunctionGenerator
from .. import VisaMixin, SCPI_Facet
from ... import u, Q_

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'AgilentMXG': ('Agilent Technologies',
                   ['N5181A']),
}


def _convert_enum(enum_type):
    """Check if arg is an instance or key of enum_type, and return that enum

    Strings are converted to lowercase first, so enum fields must be lowercase.
    """
    def convert(arg):
        if isinstance(arg, enum_type):
            return arg
        try:
            return enum_type[arg.lower()]
        except (KeyError, AttributeError):
            raise ValueError("{} is not a valid {} enum".format(arg, enum_type.__name__))
    return convert


class TriggerSource(Enum):
    bus = 'BUS'
    immediate = 'IMMMEDIATE'
    external = 'EXTERNAL'
    key = 'KEY'
    timer = 'TIMER'
    manual = 'MANUAL'


class FreqMode(Enum):
    cw = fixed = 'FIXED'
    list = 'LIST'


class AgilentMXG(FunctionGenerator, VisaMixin):
    def _initialize(self):
        self._rsrc.read_termination = '\n'

    cw_frequency = SCPI_Facet('FREQ:CW', convert=float, units='Hz')
    sweep_center_frequency = SCPI_Facet('FREQ:CENTER', convert=float, units='Hz')
    sweep_span_frequency = SCPI_Facet('FREQ:SPAN', convert=float, units='Hz')
    sweep_start_frequency = SCPI_Facet('FREQ:START', convert=float, units='Hz')
    sweep_stop_frequency = SCPI_Facet('FREQ:STOP', convert=float, units='Hz')

    freq_mode = SCPI_Facet('FREQ:MODE', convert=_convert_enum(FreqMode))

    # enabling freq and/or amplitude sweep
    # sweep triggering
    # load a list sweep file
