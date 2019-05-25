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
    'DG800': ('Rigol Technologies', ['DG812']),
}

class Rigol(FunctionGenerator, VisaMixin):
    def _initialize(self):
        self._rsrc.read_termination = '\n'

class OutputState(Enum):
    ON = True
    OFF = False

class DG800(Rigol, VisaMixin):


    frequency1 = SCPI_Facet(':SOURce1:FREQuency', convert=float, units='Hz')
    frequency2 = SCPI_Facet(':SOURce2:FREQuency', convert=float, units='Hz')
    amplitude1 = SCPI_Facet('SOURce1:VOLTage:AMPlitude', convert=float, units='V')
    amplitude2 = SCPI_Facet('SOURce2:VOLTage:AMPlitude', convert=float, units='V')
    offset1 = SCPI_Facet('SOURce1:VOLTage:OFFSet', convert=float, units='V')
    offset2 = SCPI_Facet('SOURce2:VOLTage:OFFSet', convert=float, units='V')
    output1 = SCPI_Facet('OUTPut1:STATe', convert=OutputState)

    @property
    def output1(self):
        val = self.query('OUTPut1:STATe?')
        return OutputState[val].value
    
    @output1.setter
    def output1(self, val):
        val = int(bool(val))
        self.write('OUTPut1:STATe %i' % val)

    @property
    def output2(self):
        val = self.query('OUTPut2:STATe?')
        return OutputState[val].value
    
    @output2.setter
    def output2(self, val):
        val = int(bool(val))
        self.write('OUTPut2:STATe %i' % val)

    def align(self):
        # /*Executes an align phase operation on CH1.*/        
        self._rsrc.write(':SOUR1:PHAS:INIT') 

        # /*Executes an align phase operation on CH2.*/
        # :SOUR2:PHAS:SYNC        
