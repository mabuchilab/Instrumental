# -*- coding: utf-8 -*-
# Copyright 2013-2018 Nate Bogdanowicz
"""
Driver module for Tektronix oscilloscopes. Currently supports

* TDS 3000 series
* MSO/DPO 4000 series
"""
import visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from . import Scope
from .. import VisaMixin, SCPI_Facet, Facet
from ..util import visa_context
from ... import u, Q_
from enum import Enum

MODEL_CHANNELS = {
    'DSO1024': 4,
}

class PointsMode(Enum):
    normal = 'NORMal'
    maximum = 'MAXimum'
    raw = 'RAW'

# This code is not used right now, it was a preliminary effort to do things the
# "clean" way...
class DataFormat(Enum):
    word = 'WORD'
    byte = 'BYTE'
    ascii = 'ASCii'

def infer_termination(msg_str):
    if msg_str.endswith('\r\n'):
        return '\r\n'
    elif msg_str.endswith('\r'):
        return '\r'
    elif msg_str.endswith('\n'):
        return '\n'
    return None

class AgilentScope(Scope, VisaMixin):
    """
    A base class for Agilent Technologies Scopes
    """
    
    def _initialize(self):
        msg = self.query('*IDN?')
        self._rsrc.read_termination = infer_termination(msg)
        
    points_mode = SCPI_Facet(':WAVeform:POINts:MODE', convert=PointsMode,
                                 doc="sets the type of data returned by the :WAV:DATA? query")
    points = SCPI_Facet(':WAVeform:POINts', convert=int,
                        doc="Number of points to return on :WAV:DATA?")
    
    format = SCPI_Facet(':WAVeform:FORMat',
                        doc="Format of the returned data")

    def run(self):
        """Performs continuous acquisitions"""
        self._rsrc.write(':RUN')

    def stop(self):
        """Stops continuous acquisitions"""
        self._rsrc.write(':STOP')

    def single(self):
        """Runs a single acquisition"""
        self._rsrc.write(':SINGLE')

    def capture(self, channel):
        """ Returns unitful arrays for (time, voltage)"""
        self.write(':WAVeform:SOURce CHAN%i' % channel)
        preamble = self.query(':WAVeform:PREAMBLE?')
        (fmt, typ, num_points, _, 
            x_increment, x_origin, x_reference,
            y_increment, y_origin, y_reference,
        ) = np.fromstring(preamble, sep=',')
        
        t = x_origin + (np.arange(num_points) * x_increment) * u.second
        
        if fmt == 0:
            # WORD
            dtype = 'h'
        if fmt == 1:
            # BYTE
            dtype = 'B'
        if fmt >= 0 and fmt <= 1:
            data = self._rsrc.query_binary_values(':WAVeform:DATA? CHAN%i' % channel, datatype=dtype, is_big_endian=True)
            data = (y_reference - data) * y_increment - y_origin
            return t, data * u.volt
        if fmt == 2:
            # ASCII
            data = self.query(':WAVeform:DATA? CHAN%i' % channel)
            data = np.fromstring(data[13:], sep=',') # Take off some header information
            return t, data * u.volt

class DSO_1000(AgilentScope):

    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('Agilent Technologies', ['DSO1024A'])