# -*- coding: utf-8 -*-
# Copyright 2018-2019 Nate Bogdanowicz
"""
Driver module for Agilent signal generators.

MXG driver was initially developed for and tested on the N5181A.
"""
from enum import Enum
from . import FunctionGenerator
from .. import VisaMixin, SCPI_Facet


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
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('Agilent Technologies', ['N5181A'])

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


class Agilent33250A(FunctionGenerator, VisaMixin):
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('Agilent Technologies', ['33250A'])

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    frequency = SCPI_Facet('FREQ', convert=float, units='Hz')
    voltage = SCPI_Facet('VOLT', convert=float, units='V')


class AgilentE4400B(FunctionGenerator, VisaMixin):
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('Hewlett-Packard', ['ESG-1000B'])
    def _initialize(self):
        self._rsrc.read_termination = '\n'

    frequency = SCPI_Facet('FREQ:FIXED', convert=float, units='Hz')
