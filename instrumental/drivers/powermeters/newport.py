# -*- coding: utf-8 -*-
# Copyright 2014 Chris Rogers, Nate Bogdanowicz
"""
Driver module for Newport power meters. Supports:

* 1830-C
"""

from . import PowerMeter
from .. import InstrumentTypeError, _get_visa_instrument
from ... import Q_


def _instrument(params):
    # Not sure yet how to verify this is actually an 1830-C...
    # Maybe use the status register?
    inst = _get_visa_instrument(params)

    # Will have to restore original term_chars later...
    inst.term_chars = '\n'

    return Newport_1830_C(inst)


class Newport_1830_C(PowerMeter):
    """A Newport 1830-C power meter"""

    # Status byte codes
    PARAM_ERROR = 1
    COMMAND_ERROR = 2
    SATURATED = 4
    OUT_OF_RANGE = 8
    MSG_AVAILABLE = 16
    BUSY = 32
    SERVICE_REQUEST = 64
    READY_READING = 128

    # Filter averaging constants
    SLOW_FILTER = 1
    MEDIUM_FILTER = 2
    NO_FILTER = 3

    def __init__(self, inst):
        self._inst = inst

    def get_status_byte(self):
        """
        Queries the status byte register, and returns the result as an integer.
        """
        status = self._inst.ask('Q?')
        return int(status)

    def get_power(self):
        """
        Returns the current power measurement.

        Returns
        -------
        power : Quantity
            Power in units of watts, regardless of the power meter's current
            'units' setting.
        """
        original_units = self._inst.ask('U?')
        if original_units != '1':
            self._inst.write('U1')  # Measure in watts
            power = float(self._inst.ask('D?'))
            self._inst.write('U' + original_units)
        else:
            power = float(self._inst.ask('D?'))

        return Q_(power, 'watts')

    def enable_auto_range(self):
        """Enables auto-range."""
        self.set_range(0)

    def disable_auto_range(self):
        """Disables auto-range.

        Leaves the signal range at its current position.
        """
        cur_range = self.get_range()
        self.set_range(cur_range)

    def set_range(self, range_num):
        """ Sets the range for power measurements (amplifier gain)

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
        """ Returns the current range setting as an int.

        n=1 corresponds to the lowest range, while n=8 is the highest range
        (least amplifier gain)

        Note that this does not query the status of auto-range

        Returns
        -------
        range : int
            the current range setting. Possible values are from 1-8.
        """
        val = self._inst.read("R?")
        return int(val)

    def set_wavelength(self, wavelength):
        """ Set the wavelength of the input signal. """
        wavelength = int(Q_(wavelength).to('nm').magnitude)
        self._inst.write("W{}".format(wavelength))

    def get_wavelength(self):
        """ Returns the wavelength setting of the meter """
        val = int(self._inst.ask("W?"))
        return Q_(val, 'nm')

    def enable_attenuator(self, enabled=True):
        """Set whether the power meter attenuator setting is enabled"""
        self._inst.write('A{}'.format(int(enabled)))

    def disable_attenuator(self):
        self.enable_attenuator(False)

    def attenuator_enabled(self):
        """Returns whether the attenuator is enabled.

        Returns
        -------
        enabled : bool
            whether the attenuator is enabled
        """
        val = self._inst.write('A?')
        return bool(val)

    def set_slow_filter(self):
        """Sets averaging filter to slow mode.

        The slow filter uses a 16-measurement average.
        """
        self._inst.write('F1')

    def set_medium_filter(self):
        """Sets averaging filter to medium mode.

        The medium filter uses a 4-measurement average.
        """
        self._inst.write('F2')

    def set_no_filter(self):
        """Sets averaging filter to fast mode, i.e. no averaging."""
        self._inst.write('F3')

    def get_filter(self):
        """ Returns the current setting for the filter.

        Returns
        -------
        FAST_FILTER, MEDIUM_FILTER, NO_FILTER
            mode of the averaging filter
        """
        val = self._inst.ask("F?")
        return int(val)

    def enable_hold(self, enable=True):
        """Sets whether the 'hold' mode is enabled."""
        self._inst.write('G{}'.format(int(not enable)))

    def disable_hold(self):
        """Disables 'hold' mode, enabling 'run' mode."""
        self.enable_hold(False)

    def hold_enabled(self):
        """Whether 'hold' mode is enabled.

        Returns
        -------
        enabled : bool
            True if in hold mode, False if in run mode
        """
        val = int(self._inst.ask('G?'))
        return (val == 0)

    def is_measurement_valid(self):
        """Checks if the current measurement is valid.

        The measurement is considered invalid if the power meter is saturated,
        over-range or busy.
        """
        reg = self.get_status_byte()
        is_saturated = bool(reg & self.SATURATED)
        is_over_range = bool(reg & self.OUT_OF_RANGE)
        is_busy = bool(reg & self.BUSY)

        return not (is_saturated or is_over_range or is_busy)

    def store_reference(self):
        """
        Sets the current power measurement as the reference power for future dB
        or relative measurements.
        """
        self._inst.write('S')

    def enable_zero(self, enable=True):
        """Enable/disable the zero function.

        When enabled, the next power reading is stored as a background value
        and is subtracted off of all subsequent power readings.
        """
        self._inst.write("Z{}".format(int(enable)))

    def disable_zero(self):
        """Disable the zero function."""
        self.enable_zero(False)

    def zero_enabled(self):
        """Whether the zero function is enabled."""
        val = int(self._inst.ask('Z?'))  # Need to cast to int first
        return bool(val)

    def set_units(self, units):
        """ Sets the units for displaying power measurements.

        The different unit modes are watts, dB, dBm, and REL. Each displays
        the power in a different way.

        'watts' displays absolute power in watts

        'dBm' displays power in dBm (i.e. dBm = 10 * log(P / 1mW))

        'dB' displays power in dB relative to the current reference power (i.e.
        dB = 10 * log(P / Pref). At power-up, the reference power is set to
        1mW.

        'REL' displays power relative to the current reference power (i.e.
        REL = P / Pref)

        The current reference power can be set using `store_reference`().

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
        """Get the units used for power measurments.

        Returns
        -------
        units : str
            One of 'watts', 'db', 'dbm', 'rel'
        """
        val = int(self._inst.ask('U?'))
        units = {1: 'watts', 2: 'db', 3: 'dbm', 4: 'rel'}
        return units[val]
