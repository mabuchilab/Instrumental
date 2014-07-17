# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Driver module for Thorlabs power meters. Supports:

* PM100D
"""

from . import PowerMeter
from .. import InstrumentTypeError, _get_visa_instrument
from ... import Q_


def _instrument(params):
    inst = _get_visa_instrument(params)
    idn = inst.ask("*IDN?")
    idn_list = idn.split(',')

    if len(idn_list) != 4:
        raise InstrumentTypeError("Not a Thorlabs PM100D series power meter")
    manufacturer, model, serial, firmware = idn_list

    if manufacturer != 'Thorlabs' or model != 'PM100D':
        raise InstrumentTypeError("Not a Thorlabs PM100D series power meter")
    return PM100D(inst)


class PM100D(PowerMeter):
    """A Thorlabs PM100D series power meter"""

    def __init__(self, visa_inst):
        self._inst = visa_inst

    def get_power(self):
        self._inst.write('power:dc:unit W')
        val = float(self._inst.ask('measure:power?'))
        return Q_(val, 'watts')

    def get_range(self):
        """Get the current input range's max power"""
        val = float(self._inst.ask('power:dc:range?'))
        return Q_(val, 'watts')

    def enable_auto_range(self, enable=True):
        """Enable auto-ranging"""
        enable = bool(enable)
        self._inst.write('pow:range:auto {}'.format(int(enable)))

    def disable_auto_range(self):
        """Disable auto-ranging"""
        self.enable_auto_range(False)

    def auto_range_enabled(self):
        """Whether auto-ranging is enabled"""
        val = int(self._inst.ask('power:dc:range:auto?'))
        return bool(val)

    def get_wavelength(self):
        """Get the input signal wavelength setting"""
        val = float(self._inst.ask('sense:correction:wav?'))
        return Q_(val, 'nm')

    def set_wavelength(self, wavelength):
        """Set the input signal wavelength setting"""
        wav_nm = Q_(wavelength).to('nm').magnitude
        self._inst.write('sense:correction:wav {}'.format(wav_nm))

    def get_num_averaged(self):
        """Get the number of samples to average"""
        val = int(self._inst.ask('sense:average:count?'))
        return val

    def set_num_averaged(self, num_averaged):
        """Set the number of samples to average

        Each sample takes approximately 3ms. Thus, averaging over 1000 samples
        would take about a second.

        Parameters
        ----------
        num_averaged : int
            number of samples to average
        """
        val = int(num_averaged)
        self._inst.write('sense:average:count {}'.format(val))
