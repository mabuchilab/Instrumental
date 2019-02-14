# -*- coding: utf-8  -*-
"""
Driver for ILX Lightwave Lasers
"""

from . import SpectrumAnalyzer
from .. import VisaMixin, SCPI_Facet
import numpy as np

_INST_PARAMS = ['visa_address']

class FSEA20(SpectrumAnalyzer, VisaMixin):

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    center = SCPI_Facet('FREQ:CENT', units='Hz', convert=float)
    span = SCPI_Facet('FREQ:SPAN', units='Hz', convert=float)
    start = SCPI_Facet('FREQ:STAR', units='Hz', convert=float)
    stop = SCPI_Facet('FREQ:STOP', units='Hz', convert=float)
    reference = SCPI_Facet('DISPLAY:TRACE:Y:RLEVEL', convert=float)
    sweep_time = SCPI_Facet('SWEEP:TIME', units='s', convert=float)
    vbw = SCPI_Facet('BAND:VID', units='Hz', convert=float)
    rbw = SCPI_Facet('BAND', units='Hz', convert=float)
    averages = SCPI_Facet('AVER:COUNT', convert=int)
    #attenuation = SCPI_Facet('INP1:ATT')

    def get_trace(self, channel=1):
        """Get the trace for a given channel.

        Returns a tuple (frequencies, power)

        """
        data_string = self.query('TRAC? TRACE%i' % channel)
        power = np.array(data_string.split(',')).astype(float)
        frequency = np.linspace(self.start.m, self.stop.m, len(power))
        return frequency, power
