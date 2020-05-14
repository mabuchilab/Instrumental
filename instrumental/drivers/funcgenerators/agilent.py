# -*- coding: utf-8 -*-
# Copyright 2018-2019 Nate Bogdanowicz
"""
Driver module for Agilent signal generators.

MXG driver was initially developed for and tested on the N5181A.
"""
from enum import Enum
from . import FunctionGenerator
from .. import VisaMixin, SCPI_Facet
from ... import u, Q_

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

class OnOffState(Enum):
    ON = True
    OFF = False

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
    width1 = SCPI_Facet('PULS:WIDTh1 ', convert=float, units='ns')
    width2 = SCPI_Facet('SOURce2:FUNCtion:PULSe:WIDTh', convert=float, units='s')

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    frequency = SCPI_Facet('FREQ:FIXED', convert=float, units='Hz')

class Agilent81110A(FunctionGenerator, VisaMixin):
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('HEWLETT-PACKARD', ['HP81110A'])

    def _initialize(self):
        self._rsrc.read_termination = '\n'

    def set_polarity(self, polarity, channel=1):
        """ Set the polarity of a channel.

        Parameters
        ----------
        pol : either "NORM" for normal or "INV" for inverse
        
        channel: int
            The channel number
        """
        self.write('OUTP{:d}:POL {}', channel, polarity)
    
    def get_polarity(self, channel=1):
        return self.query("OUTP{:d}:POL?", channel)

    def get_errors(self):
        return self.query('SYST:ERR?')

    def set_delay(self, delay, channel=1):
        """ Set the delay of a channel.

        Parameters
        ----------
        delay: pint.Quantity
            The new delay in nanosecond-compatible units
        
        channel: int
            The channel number
        """
        val = Q_(delay)
        mag = val.to('ns').magnitude
        self.write('PULS:DEL{:d} {}NS', channel, mag)

    def set_out_impedance(self, imp, channel=1):
        """ Set the output impedance of a channel.

        Parameters
        ----------
        imp : pint.Quantity
            The impedance value in Ohm
        
        channel: int
            The channel number
        """
        val = Q_(imp)
        mag = val.to('ohm').magnitude
        self.write('OUTP{:d}:IMP:EXT {:f}OHM', channel, mag)

    def set_width(self, width, channel=1):
        """ Set the width.

        Parameters
        ----------
        width : pint.Quantity
            The new width in nanosecond-compatible units
        
        channel: int
            Channel number
        """
        val = Q_(width)
        mag = val.to('ns').magnitude
        self.write('PULS:WIDTh{:d} {:f}NS', channel, mag)

    def set_high(self, high, channel=1):
        """ Set the high voltage level.

        This changes the high level while keeping the low level fixed.
        
        Parameters
        ----------
        high : pint.Quantity
            The new high level in volt-compatible units
        
        channel: int
            Channel number
        """
        high = Q_(high)
        mag = high.to('V').magnitude
        self.write('VOLT{:d}:HIGH {:f}V', channel, mag)

    def set_low(self, low, channel=1):
        """ Set the low voltage level.

        This changes the low level while keeping the high level fixed.

        Parameters
        ----------
        low : pint.Quantity
            The new low level in volt-compatible units
        
        channel: int
            Channel number
        """
        low = Q_(low)
        mag = low.to('V').magnitude
        self.write('VOLT{:d}:LOW {:f}V', channel, mag)

    @property
    def output1(self):
        val = self.query(':OUTP1?')
        return bool(int(val))

    @output1.setter
    def output1(self, val):
        val = int(bool(val))
        self.write('OUTP1 %s' % OnOffState(val).name)

    @property
    def output2(self):
        val = self.query('OUTP2?')
        return bool(int(val))

    @output2.setter
    def output2(self, val):
        val = int(bool(val))
        self.write('OUTP2 %s' % OnOffState(val).name)