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


class TriggerSource(Enum):
    bus = 'BUS'
    immediate = 'IMMMEDIATE'
    external = 'EXTERNAL'
    key = 'KEY'
    timer = 'TIMER'
    manual = 'MANUAL'


class AgilentMXG(FunctionGenerator, VisaMixin):
    def _initialize(self):
        self._rsrc.read_termination = '\n'

    cw_frequency = SCPI_Facet('FREQ:CW', convert=float, units='Hz')
    sweep_center_frequency = SCPI_Facet('FREQ:CENTER', convert=float, units='Hz')
    sweep_span_frequency = SCPI_Facet('FREQ:SPAN', convert=float, units='Hz')
    sweep_start_frequency = SCPI_Facet('FREQ:START', convert=float, units='Hz')
    sweep_stop_frequency = SCPI_Facet('FREQ:STOP', convert=float, units='Hz')
