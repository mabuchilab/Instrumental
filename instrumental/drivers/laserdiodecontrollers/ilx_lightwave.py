# -*- coding: utf-8  -*-
"""
Driver for ILX Lightwave Lasers
"""

from . import LaserDiodeController
from .. import VisaMixin, SCPI_Facet

_INST_PARAMS = ['visa_address']

class LDC3724B(LaserDiodeController, VisaMixin):

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    current = SCPI_Facet('LAS:LDI', units='mA', convert=float)
    temperature = SCPI_Facet('TEC:T', units='degC', convert=float)
