# -*- coding: utf-8 -*-
# Copyright 2014 Chris Rogers, Nate Bogdanowicz
"""
Driver module for Newport power meters. Supports:

* 1830-C
"""

from . import PowerMeter
from .. import _get_visa_instrument
from ... import Q_


def _instrument(params):
    # Not sure yet how to verify this is actually an 1830-C...
    # Maybe use the status register?
    inst = _get_visa_instrument(params)

    # Will have to restore original term_chars later...
    inst.read_termination = '\n'
    inst.write_termination = '\n'

    return Newport_1830_C(inst)


class Newport_1830_C(PowerMeter):
    """A Newport 1830-C power meter"""

    # Status byte codes
    _PARAM_ERROR = 1
    _COMMAND_ERROR = 2
    _SATURATED = 4
    _OUT_OF_RANGE = 8
    _MSG_AVAILABLE = 16
    _BUSY = 32
    _SERVICE_REQUEST = 64
    _READY_READING = 128

    # Filter averaging constants
    SLOW_FILTER = 1
    MEDIUM_FILTER = 2
    NO_FILTER = 3

    def __init__(self, inst):
        self._inst = inst

    def get_status_byte(self):
        """Query the status byte register and return it as an int"""
        status = self._inst.query('Q?')
        return int(status)

    def get_power(self):
        """Get the current power measurement

        Returns
        -------
        power : Quantity
            Power in units of watts, regardless of the power meter's current
            'units' setting.
        """
        original_units = self._inst.query('U?')
        if original_units != '1':
            self._inst.write('U1')  # Measure in watts
            power = float(self._inst.query('D?'))
            self._inst.write('U' + original_units)
        else:
            power = float(self._inst.query('D?'))

        return Q_(power, 'watts')

    def enable_auto_range(self):
        """Enable auto-range"""
        self.set_range(0)

    def disable_auto_range(self):
        """Disable auto-range

        Leaves the signal range at its current position.
        """
        cur_range = self.get_range()
        self.set_range(cur_range)

    def set_range(self, range_num):
        """Set the range for power measurements

        range_num = 0 for auto-range
        range_num = 1 to 8 for manual signal range
        (1 is lowest, and 8 is highest)

        Parameters
        ----------
        n : int
            Sets the signal range for the input signal.
        """
        self._inst.write('R{}'.format(int(range_num)))

    def get_range(self):
        """Return the current range setting as an int

        1 corresponds to the lowest range, while 8 is the highest range (least
        amplifier gain).

        Note that this does not query the status of auto-range.

        Returns
        -------
        range : int
            the current range setting. Possible values are from 1-8.
        """
        val = self._inst.read("R?")
        return int(val)

    def set_wavelength(self, wavelength):
        """Set the input signal wavelength setting

        Parameters
        ----------
        wavelength : Quantity
            wavelength of the input signal, in units of [length]
        """
        wavelength = int(Q_(wavelength).to('nm').magnitude)
        self._inst.write("W{}".format(wavelength))

    def get_wavelength(self):
        """Get the input wavelength setting"""
        val = int(self._inst.query("W?"))
        return Q_(val, 'nm')

    def enable_attenuator(self, enabled=True):
        """Enable the power meter attenuator"""
        self._inst.write('A{}'.format(int(enabled)))

    def disable_attenuator(self):
        """Disable the power meter attenuator"""
        self.enable_attenuator(False)

    def attenuator_enabled(self):
        """Whether the attenuator is enabled

        Returns
        -------
        enabled : bool
            whether the attenuator is enabled
        """
        val = self._inst.write('A?')
        return bool(val)

    def set_slow_filter(self):
        """Set the averaging filter to slow mode

        The slow filter uses a 16-measurement running average.
        """
        self._inst.write('F1')

    def set_medium_filter(self):
        """Set the averaging filter to medium mode

        The medium filter uses a 4-measurement running average.
        """
        self._inst.write('F2')

    def set_no_filter(self):
        """Set the averaging filter to fast mode, i.e. no averaging"""
        self._inst.write('F3')

    def get_filter(self):
        """Get the current setting for the averaging filter

        Returns
        -------
        SLOW_FILTER, MEDIUM_FILTER, NO_FILTER
            the current averaging filter
        """
        val = self._inst.query("F?")
        return int(val)

    def enable_hold(self, enable=True):
        """Enable hold mode"""
        self._inst.write('G{}'.format(int(not enable)))

    def disable_hold(self):
        """Disable hold mode"""
        self.enable_hold(False)

    def hold_enabled(self):
        """Whether hold mode is enabled

        Returns
        -------
        enabled : bool
            True if in hold mode, False if in run mode
        """
        val = int(self._inst.query('G?'))
        return (val == 0)

    def is_measurement_valid(self):
        """Whether the current measurement is valid

        The measurement is considered invalid if the power meter is saturated,
        over-range or busy.
        """
        reg = self.get_status_byte()
        is_saturated = bool(reg & self._SATURATED)
        is_over_range = bool(reg & self._OUT_OF_RANGE)
        is_busy = bool(reg & self._BUSY)

        return not (is_saturated or is_over_range or is_busy)

    def store_reference(self):
        """Store the current power input as a reference

        Sets the current power measurement as the reference power for future dB
        or relative measurements.
        """
        self._inst.write('S')

    def enable_zero(self, enable=True):
        """Enable the zero function

        When enabled, the next power reading is stored as a background value
        and is subtracted off of all subsequent power readings.
        """
        self._inst.write("Z{}".format(int(enable)))

    def disable_zero(self):
        """Disable the zero function"""
        self.enable_zero(False)

    def zero_enabled(self):
        """Whether the zero function is enabled"""
        val = int(self._inst.query('Z?'))  # Need to cast to int first
        return bool(val)

    def set_units(self, units):
        """Set the units for displaying power measurements

        The different unit modes are watts, dB, dBm, and REL. Each displays
        the power in a different way.

        'watts' displays absolute power in watts

        'dBm' displays power in dBm (i.e. dBm = 10 * log(P / 1mW))

        'dB' displays power in dB relative to the current reference power (i.e.
        dB = 10 * log(P / Pref). At power-up, the reference power is set to
        1mW.

        'REL' displays power relative to the current reference power (i.e.
        REL = P / Pref)

        The current reference power can be set using `store_reference()`.

        Parameters
        ----------
        units : 'watts', 'dBm', 'dB', or 'REL'
            Case-insensitive str indicating which units mode to enter.
        """
        units = units.lower()
        valid_units = {'watts': 1, 'dbm': 2, 'db': 3, 'rel': 4}

        if units not in valid_units:
            raise Exception("`units` must be one of 'watts', 'dbm', 'db', or 'rel")

        self._inst.write('U{}'.format(valid_units[units]))

    def get_units(self):
        """Get the units used for displaying power measurements

        Returns
        -------
        units : str
            'watts', 'db', 'dbm', or 'rel'
        """
        val = int(self._inst.query('U?'))
        units = {1: 'watts', 2: 'db', 3: 'dbm', 4: 'rel'}
        return units[val]
