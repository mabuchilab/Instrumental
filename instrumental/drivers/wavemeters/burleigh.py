# -*- coding: utf-8 -*-
# Copyright 2014-2017 Nate Bogdanowicz
"""
Driver module for Burleigh wavemeters. Supports:

* WA-1000/1500
"""
import warnings
import time

from . import Wavemeter
from ..util import visa_timeout_context
from ... import Q_

_INST_PRIORITY = 9
_INST_PARAMS = ['visa_address']

# Constants; See Appendix A of WA-1000/1500 manual for details
# 'Hard' command codes
_BTN_0 = b'@\x00'
_BTN_1 = b'@\x01'
_BTN_2 = b'@\x02'
_BTN_3 = b'@\x03'
_BTN_4 = b'@\x04'
_BTN_5 = b'@\x05'
_BTN_6 = b'@\x06'
_BTN_7 = b'@\x07'
_BTN_8 = b'@\x08'
_BTN_9 = b'@\x09'
_BTN_CLEAR = b'@\x0A'
_BTN_DOT = b'@\x0B'
_BTN_ENTER = b'@\x0C'
_BTN_REMOTE = b'@\x0D'
_BTN_SAVE = b'@\x0E'
_BTN_RESET = b'@\x0F'
_BTN_MANUAL_DEATTENUATE = b'@\x10'
_BTN_MANUAL_ATTENUATE = b'@\x11'
_BTN_AUTO_ATTENUATE = b'@\x13'
_BTN_HUMIDITY = b'@\x20'
_BTN_PRESSURE = b'@\x21'
_BTN_TEMPERATURE = b'@\x22'
_BTN_NUM_AVERAGED = b'@\x23'
_BTN_ANALOG_RES = b'@\x24'
_BTN_DISPLAY_RES = b'@\x25'
_BTN_SETPOINT = b'@\x26'
_BTN_UNITS = b'@\x27'
_BTN_DISPLAY = b'@\x28'
_BTN_MEDIUM = b'@\x29'
_BTN_RESOLUTION = b'@\x2A'
_BTN_AVERAGING = b'@\x2B'

_CHAR_TO_BTN = {
    '0': _BTN_0,
    '1': _BTN_1,
    '2': _BTN_2,
    '3': _BTN_3,
    '4': _BTN_4,
    '5': _BTN_5,
    '6': _BTN_6,
    '7': _BTN_7,
    '8': _BTN_8,
    '9': _BTN_9,
    '.': _BTN_DOT
}

# 'Soft' command codes
_SET_BROADCAST = b'@\x42'
_SET_DEVIATION_ON = b'@\x44'
_SET_QUERY = b'@\x51'
_SET_DEVIATION_OFF = b'@\x55'

# Display LED masks
_MASK_UNITS_NM = 0x0009
_MASK_UNITS_WAVENUMBER = 0x0012
_MASK_UNITS_GHZ = 0x0024
_MASK_DISPLAY_WAVELENGTH = 0x0040
_MASK_DISPLAY_DEVIATION = 0x0080
_MASK_MEDIUM_AIR = 0x0100
_MASK_MEDIUM_VACUUM = 0x0200
_MASK_RES_FIXED = 0x0400
_MASK_RES_AUTO = 0x0800
_MASK_AVERAGING_ON = 0x1000
_MASK_AVERAGING_OFF = 0x2000

# System LED masks
_MASK_DISPLAY_RES = 0x0001
_MASK_SETPOINT = 0x0002
_MASK_NUM_AVERAGED = 0x0004
_MASK_ANALOG_RES = 0x0008
_MASK_PRESSURE = 0x0010
_MASK_TEMPERATURE = 0x0020
_MASK_HUMIDITY = 0x0040
_MASK_SETUP = 0x0080
_MASK_REMOTE = 0x0100
_MASK_ATTENUATOR_AUTO = 0x0200
_MASK_ATTENUATOR_MANUAL = 0x0400

# Convenience masks
_MASK_DISPLAYING_STATES = 0x004F

_SYS_MASK_TO_CMD = {
    _MASK_DISPLAY_RES: _BTN_RESOLUTION,
    _MASK_SETPOINT: _BTN_SETPOINT,
    _MASK_NUM_AVERAGED: _BTN_NUM_AVERAGED,
    _MASK_ANALOG_RES: _BTN_ANALOG_RES,
    _MASK_PRESSURE: _BTN_PRESSURE,
    _MASK_TEMPERATURE: _BTN_TEMPERATURE,
    _MASK_HUMIDITY: _BTN_HUMIDITY
}


def _check_visa_support(visa_inst):
    with visa_timeout_context(visa_inst, 50):
        try:
            # Check that we get a vaguely Burleigh-like response
            resp = visa_inst.query(_SET_QUERY)
            if resp.count(b',') == 2:
                visa_inst.clear()
                return 'WA_1000'
        except:
            pass
    return None


class WA_1000(Wavemeter):
    """A Burleigh WA-1000/1500 wavemeter"""
    def _initialize(self):
        self._rsrc.read_termination = '\r\n'
        self._rsrc.write_termination = '\r\n'
        self.reload_needed = False

        # Disable broadcast mode and clear the buffer
        self._rsrc.query(_SET_QUERY)  # Use query to dump the response
        self._rsrc.clear()

    def _load_state(self):
        """Query the meter and set self.(disp_str, disp_leds, sys_leds)"""
        response = self._rsrc.query(_SET_QUERY)
        self.disp_str, disp_leds, sys_leds = response.split(b',')
        self.disp_leds = int(disp_leds, 16)
        self.sys_leds = int(sys_leds, 16)
        self.reload_needed = False

    def _reload_if_needed(self):
        if self.reload_needed:
            self._load_state()

    def _write_float(self, num):
        self._rsrc.write(_BTN_CLEAR)

        num_str = '{:.4f}'.format(float(num))
        for char in num_str:
            self._rsrc.write(_CHAR_TO_BTN[char])

            # Need to wait for button presses to register
            time.sleep(0.01)

        self._rsrc.write(_BTN_ENTER)

    def _write_int(self, num):
        self._rsrc.write(_BTN_CLEAR)

        num_str = '{:d}'.format(int(num))
        for char in num_str:
            self._rsrc.write(_CHAR_TO_BTN[char])

            # Need to wait for button presses to register
            time.sleep(0.01)

        self._rsrc.write(_BTN_ENTER)

    def _clear_sys_state(self):
        """Unset any system state that is selected"""
        if self.sys_leds & _MASK_DISPLAYING_STATES:
            cmd_byte = _SYS_MASK_TO_CMD[self.sys_leds & _MASK_DISPLAYING_STATES]
            self._rsrc.write(cmd_byte)
            self.reload_needed = True

    def _show_setpoint(self):
        if not (self.sys_leds & _MASK_SETPOINT):
            self._rsrc.write(_BTN_SETPOINT)
            self.reload_needed = True

    def _show_num_averaged(self):
        if not (self.sys_leds & _MASK_NUM_AVERAGED):
            self._rsrc.write(_BTN_NUM_AVERAGED)
            self.reload_needed = True

    def _show_temperature(self):
        if not (self.sys_leds & _MASK_TEMPERATURE):
            self._rsrc.write(_BTN_TEMPERATURE)
            self.reload_needed = True

    def _show_pressure(self):
        if not (self.sys_leds & _MASK_PRESSURE):
            self._rsrc.write(_BTN_PRESSURE)
            self.reload_needed = True

    def _toggle_to_wavelength(self):
        """Toggles the deviation/wavelength setting to wavelength"""
        if self.disp_leds & _MASK_DISPLAY_DEVIATION:
            self._rsrc.write(_BTN_DISPLAY)
            self.reload_needed = True

    def _toggle_to_deviation(self):
        """Toggles the deviation/wavelength setting to deviation"""
        if self.disp_leds & _MASK_DISPLAY_WAVELENGTH:
            self._rsrc.write(_BTN_DISPLAY)
            self.reload_needed = True

    def _toggle_units_to_nm(self):
        if self.disp_leds & _MASK_UNITS_WAVENUMBER:
            self._rsrc.write(_BTN_UNITS)
            self._rsrc.write(_BTN_UNITS)
            self.reload_needed = True
        elif self.disp_leds & _MASK_UNITS_GHZ:
            self._rsrc.write(_BTN_UNITS)
            self.reload_needed = True

    def _toggle_medium_to_vacuum(self):
        if self.disp_leds & _MASK_MEDIUM_AIR:
            self._rsrc.write(_BTN_MEDIUM)
            self.reload_needed = True

    def _handle_bad_disp_str(self):
        s = self.disp_str[1:].strip()
        if s == b'LO SIG':
            raise Exception("Input signal power is too low")
        elif s == b'HI SIG':
            raise Exception("Input signal power is too high")
        else:
            raise Exception("Unrecognized display string '{}'".format(self.disp_str))

    def _get_wav_dev(self, want_deviation):
        self._load_state()
        self.reload_needed = False

        # Switch to displaying wavelength/deviation in nm
        self._clear_sys_state()
        self._toggle_units_to_nm()
        self._toggle_medium_to_vacuum()

        if want_deviation:
            self._toggle_to_deviation()
        else:
            self._toggle_to_wavelength()

        if self.reload_needed:
            self._load_state()

        # Check for uncertainty
        sign = self.disp_str[0]
        if sign == b'~':
            warnings.warn("An instability has been detected in the input "
                          "laser system that may cause increased "
                          "uncertainty in the measurement")

        # Parse rest of the wavelength display string
        try:
            value = float(self.disp_str[1:])
        except ValueError:
            self._handle_bad_disp_str()

        return Q_(value, 'nm')

    def get_wavelength(self):
        """Get the wavelength

        Returns
        -------
        wavelength : Quantity
            The current input wavelength measurement
        """
        return self._get_wav_dev(want_deviation=False)

    def get_deviation(self):
        """Get the current deviation

        Returns
        -------
        deviation : Quantity
            The wavelength difference between the current input wavelength
            and the fixed setpoint.
        """
        return self._get_wav_dev(want_deviation=True)

    def get_setpoint(self):
        """Get the wavelength setpoint

        Returns
        -------
        setpoint : Quantity
            the wavelength setpoint
        """
        self._load_state()
        self.reload_needed = False

        self._show_setpoint()
        self._toggle_units_to_nm()

        if self.reload_needed:
            self._load_state()

        try:
            value = float(self.disp_str[1:])
        except ValueError:
            self._handle_bad_disp_str()

        return Q_(value, 'nm')

    def set_setpoint(self, setpoint):
        """Set the wavelength setpoint

        The setpoint is a fixed wavelength used to compute the deviation. It is
        used for display and to determine the analog output voltage.

        Parameters
        ----------
        setpoint : Quantity
            Wavelength of the setpoint, in units of [length]
        """
        setpoint = Q_(setpoint).to('nm')

        self._show_setpoint()
        self._toggle_units_to_nm()

        self._write_float(setpoint.magnitude)

    def get_num_averaged(self):
        """Get the number of samples used in averaging mode"""
        self._load_state()

        self._show_num_averaged()
        self._reload_if_needed()

        try:
            num_averaged = int(self.disp_str)
        except ValueError:
            self._handle_bad_disp_str()

        return num_averaged

    def set_num_averaged(self, num):
        """Set the number of samples used in averaging mode

        When averaging mode is enabled, the wavemeter calculates a running
        average of the last `num` samples.

        Parameters
        ----------
        num : int
            Number of samples to average. Must be between 2 and 50.
        """
        num = int(num)
        if not (2 <= num <= 50):
            raise Exception("`num` must be between 2 and 50")

        self._show_num_averaged()
        self._write_int(num)

    def enable_averaging(self, enable=True):
        """Enable averaging mode"""
        if not (enable == self.averaging_enabled()):
            self._clear_sys_state()
            self._rsrc.write(_BTN_AVERAGING)

    def disable_averaging(self):
        """Disable averaging mode"""
        self.enable_averaging(False)

    def averaging_enabled(self):
        """Whether averaging mode is enabled"""
        self._load_state()
        return bool(self.disp_leds & _MASK_AVERAGING_ON)

    def get_temperature(self):
        """Get the temperature inside the wavemeter

        Returns
        -------
        temperature : Quantity
            The temperature inside the wavemeter
        """
        self._load_state()

        self._show_temperature()
        self._reload_if_needed()

        try:
            temp = float(self.disp_str)
        except ValueError:
            self._handle_bad_disp_str()

        return Q_(temp, 'degC')

    def get_pressure(self):
        """Get the barometric pressure inside the wavemeter

        Returns
        -------
        pressure : Quantity
            The barometric pressure inside the wavemeter
        """
        self._load_state()

        self._show_pressure()
        self._reload_if_needed()

        try:
            pressure = float(self.disp_str)
        except ValueError:
            self._handle_bad_disp_str()

        return Q_(pressure, 'mmHg')

    def lock(self, lock=True):
        """Lock the front panel of the wavemeter, preventing manual input

        When locked, the wavemeter can only be controlled remotely by a
        computer. To unlock, use `unlock()` or hit the 'Remote' button on the
        wavemeter's front panel.
        """
        if not (lock == self.is_locked()):
            self._rsrc.write(_BTN_REMOTE)

    def unlock(self):
        """Unlock the front panel of the wavemeter, allowing manual input"""
        self.lock(False)

    def is_locked(self):
        """Whether the front panel is locked or not"""
        self._load_state()
        return bool(self.sys_leds & _MASK_REMOTE)
