# -*- coding: utf-8 -*-
# Copyright 2017-2018 Dodd Gray and Nate Bogdanowicz
"""
Driver for VISA control of Covesion OC2 crystal oven temperature controller
"""

from __future__ import print_function

import time

from pyvisa.errors import VisaIOError
from pyvisa.constants import Parity, VI_ERROR_TMO, VI_ERROR_ASRL_OVERRUN

from . import TempController
from .. import VisaMixin, Facet
from ..util import visa_context, check_units
from ... import u, Q_
from ...errors import TimeoutError


_INST_PARAMS = ['visa_address']
_INST_CLASSES = ['CovesionOC']

# Commands by letter, deduced from LabVIEW code
# Includes the fields that can be read, with their printf-style format
#
# (a) Set control variables
#    (%d)   Control type
#    (%.3f) Proportional gain
#    (%.3f) Integral
#    (%.3f) Derivative
#    (%.3f) Derivative TC
#    (%.3f) Dead Band
#    (%d)   Power up state
#
# (b) Read control variables
#    (%1d)  Control type
#    (%.3f) Proportional gain
#    (%.3f) Integral
#    (%.3f) Derivative
#    (%.3f) Derivative TC
#    (%.3f) Dead Band
#    (%d)   Power up state
#
# (c) Set alarm
#    (%d)   Alarms
#    (%.3f) Alarm min
#    (%.3f) Alarm max
#    (%.3f) Temp ok min
#    (%.3f) Temp ok max
#    (%.3f) Temp limit min
#    (%.3f) Temp limit max
#
# (d) Read alarms
#    (%d) Alarms
#    (%f) Alarm min
#    (%f) Alarm max
#    (%f) Temp ok min
#    (%f) Temp ok max
#    (%f) Temp limit min
#    (%f) Temp limit max
#
# (e) Set sensor
#    (%.0f) Sensor
#    (%.3f) X2 coeff
#    (%.3f) X coeff
#    (%.3f) C coeff
#    (%s)   Unit
#    (%d)   Averaging
#
# (f) Read sensor
#    (%d)  Sensor
#    (%f)  X2 coeff
#    (%f)  X coeff
#    (%f)  C coeff
#    (%1s) Unit
#    (%d)  Averaging
#
# (g) Set output variables
#    (%d)   Output
#    (%.3f) Output min %
#    (%.3f) Output max %
#    (%.3f) Output freq
#
# (h) Read output variables
#    (%d) Output
#    (%f) Output min %
#    (%f) Output max %
#    (%f) Output freq
#
# (i) Set the setpoint
#    (%.0f) Setpoint
#    (%.3f) Pot range
#    (%.3f) Value
#    (%.3f) Pot offset
#    (%.0f) Rate deg/V
#    (%.2f) X coeff deg/V
#    (%.2f) C coeff deg
#
# (j) Read the setpoint
#    (%0f) Setpoint
#    (%0f) Temperature
#    (%1d) Control
#    (%0f) Output %
#    (%1d) Alarms
#    (%1d) Faults
#    (%1d) TEMP OK
#    (%0f) Supply VDC
#    (%0f) Version
#    (%1d) Test cycle
#    (%1d) Test Mode
#
# (m) Set output drive
#    (%d)   Control output
#    (%.0f) Output %
#
# (n) Set mode
#    (%1d) Mode Channel 1


# Option values for certain fields
#
# Control type
#    0 (Off)
#    1 (On/Off)
#    2 (P)
#    3 (PI)
#    4 (PID)
#
# Power up state
#    0 (Off)
#    1 (On)
#    2 (Last)
#
# Alarms
#    0 (Off)
#    1 (Min)
#    2 (Max)
#    3 (Both)
#
# Sensor
#    0 (None)
#    1 (PT100)
#    2 (LM35)
#    3 (LM50)
#    4 (LM51)
#    5 (LM60)
#    6 (LM61)
#    7 (Other)
#
# Unit
#    C
#    F
#    K
#
# Averaging
#    0 (Off)
#    1 (On)
#
# Output
#    0 (Negative)
#    1 (Positive)
#
# Control Output
#    0 (Off)
#    1 (On)
#
# Setpoint
#    0 (Pot)
#    1 (Value)


DATA_FORMAT = {
    b'j': (
        ('setpoint', float),
        ('temperature', float),
        ('control', int),
        ('output', float),
        ('alarms', int),
        ('faults', int),
        ('temp_ok', int),
        ('supply_vdc', float),
        ('version', bytes.decode),
        ('test_cycle', int),
        ('test_mode', int),
    )
}


def _is_CovesionOC(rsrc):
    with visa_context(rsrc, read_termination='\r\n', baud_rate=19200,
                      timeout=1000):
        # Try twice in case of serial errors
        for _ in range(2):
            try:
                msg = rsrc.read_raw().rstrip()
                break
            except VisaIOError as e:
                if e.error_code == VI_ERROR_TMO:
                    return False
        else:
            return False
    try:
        parse_message(msg)
    except:
        return False

    return True


def _check_visa_support(rsrc):
    if rsrc.resource_name.startswith('ASRL') and _is_CovesionOC(rsrc):
        return 'CovesionOC'
    return None


def grab_latest_message(rsrc):
    msg = None
    with visa_context(rsrc, timeout=0):
        while True:
            try:
                msg = rsrc.read_raw().rstrip()
            except VisaIOError as e:
                if e.error_code == VI_ERROR_TMO:
                    break
                elif e.error_code == VI_ERROR_ASRL_OVERRUN:
                    continue
                raise
    if msg is None:
        msg = rsrc.read_raw().rstrip()
    return msg


def parse_message(msg):
    """Parse a message into a {field: value} dict and check the checksum"""
    assert msg[0:1] == b'\x01'

    cmd = msg[1:2]
    data_len = int(msg[2:4])
    assert len(msg) == data_len + 6

    data = msg[4:].split(b';')
    checksum = int(data.pop(-1), base=16)
    calc_checksum = sum(bytearray(msg[:-2])) % 256
    assert checksum == calc_checksum

    return process_data(cmd, data)


def read_latest_message(rsrc):
    """Read the most recent message from the controller, waiting if necessary

    The controller appears to constantly spit out messages, which pile up in the serial buffer. So,
    if you grab the first message in the queue, it may be quite old. This function reads out all the
    messages in the buffer, retaining the last one. If the buffer is empty, it will block (up to the
    current serial timeout setting). Returns a {field: value} dict.
    """
    msg = grab_latest_message(rsrc)
    return parse_message(msg)


def process_data(cmd, data):
    cmd_tup = DATA_FORMAT[cmd]
    return {e[0]:e[1](v) for e,v in zip(cmd_tup, data)}


class CovesionOC(TempController, VisaMixin):
    """Class definition for a Covesion OC1 and OC2 oven temperature controllers."""

    def _initialize(self):
        self.resource.parity = Parity.none
        self.resource.baud_rate = 19200
        self.resource.read_termination = '\r\n'
        self.resource.write_termination = '\n'
        self.resource.timeout = 500

    def _read_status(self):
        return read_latest_message(self.resource)

    @Facet(units='degC')
    def current_temperature(self):
        return self._read_status()['temperature']

    @Facet(units='degC')
    def temperature_setpoint(self):
        return self._read_status()['setpoint']

    @check_units(setpoint='degC')
    def _write_setpoint(self, setpoint):
        """Write a temperature setpoint to the device"""
        setpoint_C = setpoint.m_as('degC')
        data = b'%1d;%.3f;%.3f;%.3f;%.0f;%.2f;%.2f;' % (1, setpoint_C, 25., 0., 25., 100., 0.)
        base_msg = b'\x01i%02d%s' % (len(data), data)
        checksum = sum(bytearray(base_msg)) % 256
        msg = b'%s%02x' % (base_msg, checksum)
        self.resource.write_raw(msg)

    @check_units(setpoint='degC')
    def _ramp_to_setpoint(self, setpoint):
        self._start_temp = self.current_temperature
        self._final_temp = setpoint

        ramp_rate = Q_(10, 'delta_degC/minute')
        delta_T = abs(self._final_temp - self._start_temp)
        self._ramp_time = delta_T / ramp_rate
        cur_time = time.time() * u.s
        self._ramp_end_time = cur_time + self._ramp_time

        while cur_time < self._ramp_end_time:
            cur_setpoint = self._current_ramp_setpoint()
            self._write_setpoint(cur_setpoint)
            time.sleep(1.)
            cur_time = time.time() * u.s
        self._write_setpoint(self._final_temp)

    def _current_ramp_setpoint(self):
        frac_time_left = (self._ramp_end_time - time.time()*u.s) / self._ramp_time
        return self._final_temp + (self._start_temp - self._final_temp) * frac_time_left

    @check_units(temperature='degC', max_err='delta_degC', timeout='s')
    def _wait_for_temperature(self, temperature, max_err, n_samples, timeout):
        errors = [2*max_err] * n_samples

        cur_time_s = time.time()
        stop_time_s = cur_time_s + timeout.m_as('s')

        i = 0
        while any(e > max_err for e in errors) and (cur_time_s < stop_time_s):
            errors[i] = abs(self.current_temperature - temperature)
            i = (i+1) % n_samples
            cur_time_s = time.time()

        if cur_time_s >= stop_time_s:
            raise TimeoutError('Timeout while waiting for Covesion OC1 to reach temperature '
                               '{:~.2f}'.format(temperature))

    @check_units(setpoint='degC', max_err='delta_degC', timeout='s')
    def set_setpoint_and_wait(self, setpoint, max_err='0.1 delta_degC', n_samples=10,
                              timeout='5 min'):
        """Set the temperature setpoint and wait until it is reached

        Parameters
        ----------
        setpoint : Pint Quantity
            Set temperature to be sent to Covesion OC. Should be provided in
            degC units.
        max_error : Pint Quantity, optional
            Maximum temperature error that can be recorded over n_samples
            current temperature checks such that the temperature is considered
            stable. Provided in units of degK, delta_degC, or delta_degF.
        n_samples : int, optional
            Number checks for which the current temperature must be found to
            be within max_error of set_temp so that the temperature is
            considered stable.
        timeout: Pint Quantity
            Time to wait until TimeoutError is raised. Can be provided in any units of time.
        """
        self._ramp_to_setpoint(setpoint)
        self._wait_for_temperature(setpoint, max_err, n_samples, timeout)
