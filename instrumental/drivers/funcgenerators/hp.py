# -*- coding: utf-8 -*-
# Copyright 2018 Nate Bogdanowicz and Dodd Gray
"""
Driver module for HP/Agilent 8340A 10MHz-26GHz Synthesized Sweeper
"""
from enum import Enum
from . import FunctionGenerator
from .. import VisaMixin, Facet
from ...log import get_logger
from ..util import as_enum, check_enums, visa_context
from ... import u, Q_
import numpy as np

_INST_PARAMS = ['visa_address']
# _INST_VISA_INFO = {
#     'HP8340A': ('HEWLETT-PACKARD', ['34401A']),
# }

# the 8340A does not respond to *IDN? queries so you need to open it
# using its GPIB address directly, eg:
# ss =  instrument(module='funcgenerators.hp',classname='HP8340A',visa_address='GPIB0::18::INSTR')



class HP8340A(FunctionGenerator, VisaMixin):
    """Class definition for an HP 8340A 10MHz-26GHz Sythensized Sweeper. This
    instrument listen only for the most part although it can repspond with
    status bytes. I have not implemented decoding these status bytes yet.
    """
    def _initialize(self):
        pass

    def instrument_presets(self):
        """
        Send command to 8340A to return to instrument preset settings
        """
        self._rsrc.write('IP')

    def cw_frequency(self,f):
        """
        Send command to 8340A to output constant frequency
        inputs:
        f: desired frequency, pint quantity in frequency units
        """
        f_GHz = f.to(u.GHz).m
        self._rsrc.write('CW{:4.4g}GZ'.format(f_GHz))

    def set_power_level(self,pl):
        """
        Send command to 8340A to output constant frequency
        inputs:
        pl: desired power level, unitless for dbm
        """
        self._rsrc.write('PL{:3.4f}DB'.format(pl))
