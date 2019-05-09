# -*- coding: utf-8  -*-
"""
Driver for ILX Lightwave Lasers
"""

from . import LaserDiodeController
from .. import VisaMixin, SCPI_Facet


class LDC3724B(LaserDiodeController, VisaMixin):
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('ILX Lightwave', ['3724B'])

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    current = SCPI_Facet('LAS:LDI', units='mA', convert=float)
    temperature = SCPI_Facet('TEC:T', units='degC', convert=float)
