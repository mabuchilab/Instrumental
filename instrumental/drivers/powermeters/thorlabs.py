# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nate Bogdanowicz
"""
Driver module for Thorlabs power meters. Supports:

* PM100D
"""

import numpy
from . import PowerMeter
from .. import _get_visa_instrument, _ParamDict
from ...errors import InstrumentTypeError
from ... import Q_


def _instrument(params):
    inst = _get_visa_instrument(params)
    idn = inst.query("*IDN?")
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
        self._register_close_atexit()
        self._inst = visa_inst
        self._param_dict = _ParamDict(self.__class__.__name__)
        self._param_dict['module'] = 'powermeters.thorlabs'
        self._param_dict['visa_address'] = self._inst.resource_name

    def close(self):
        self._inst.control_ren(False)  # Disable remote mode

    def get_power(self):
        """Get the current power measurement

        Returns
        -------
        power : Quantity
            the current power measurement
        """
        self._inst.write('power:dc:unit W')
        val = float(self._inst.query('measure:power?'))
        return Q_(val, 'watts')

    def get_range(self):
        """Get the current input range's max power"""
        val = float(self._inst.query('power:dc:range?'))
        return Q_(val, 'watts')

    def enable_auto_range(self, enable=True):
        """Enable auto-ranging"""
        enable = bool(enable)
        self._inst.write('pow:range:auto {}'.format(int(enable)))

    def disable_auto_range(self):
        """Disable auto-ranging"""
        self.enable_auto_range(False)

    def auto_range_enabled(self):
        """Whether auto-ranging is enabled

        Returns
        -------
        bool : enabled
        """
        val = int(self._inst.query('power:dc:range:auto?'))
        return bool(val)

    def get_wavelength(self):
        """Get the input signal wavelength setting

        Returns
        -------
        wavelength : Quantity
            the input signal wavelength in units of [length]
        """
        val = float(self._inst.query('sense:correction:wav?'))
        return Q_(val, 'nm')

    def set_wavelength(self, wavelength):
        """Set the input signal wavelength setting

        Parameters
        ----------
        wavelength : Quantity
            the input signal wavelength in units of [length]
        """
        wav_nm = Q_(wavelength).to('nm').magnitude
        self._inst.write('sense:correction:wav {}'.format(wav_nm))

    def get_num_averaged(self):
        """Get the number of samples to average

        Returns
        -------
        num_averaged : int
            number of samples that are averaged
        """
        val = int(self._inst.query('sense:average:count?'))
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

    def measure(self, n_samples=100):
        """Make a multi-sample power measurement

        Parameters
        ----------
        n_samples : int
            Number of samples to take

        Returns
        -------
        pint.Measurement
            Measured power, with units and uncertainty, as a `pint.Measurement` object
        """
        n_avg = self.get_num_averaged()  # Save for later
        self.set_num_averaged(1)
        self._inst.write('power:dc:unit W')

        raw_arr = numpy.empty((n_samples,), dtype='f')
        for i in range(n_samples):
            raw_arr[i] = float(self._inst.query('measure:power?'))
        self.set_num_averaged(n_avg)

        return Q_(raw_arr.mean(), 'W').plus_minus(raw_arr.std())
