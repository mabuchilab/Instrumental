# -*- coding: utf-8 -*-
# Copyright 2017-2018 Dodd Gray and Nate Bogdanowicz
"""
Driver for VISA control of Covesion OC2 crystal oven temperature controller
"""

from __future__ import print_function

from sys import stdout
import time
from time import sleep
from datetime import timedelta

import numpy as np
from pyvisa.constants import Parity
from pyvisa import ResourceManager

from . import TempController
from .. import ParamSet
from ... import u, Q_


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
OC_parity = Parity.none
OC_baud_rate = 19200
OC_data_bits = 8
OC_read_termination = '\r'
OC_flow_control = 0
OC_timeout = 500
OC_status_keys = ['set point',
                  'temperature',
                  'control',
                  'output %',
                  'alarms',
                  'faults',
                  'temp ok',
                  'supply vdc',
                  'version',
                  'test cycle',
                  'test mode']
rm = ResourceManager()


def print_statusline(msg):
    last_msg_length = len(print_statusline.last_msg) if hasattr(print_statusline, 'last_msg') else 0
    print(' ' * last_msg_length, end='\r')
    print(msg, end='\r')
    stdout.flush()
    print_statusline.last_msg = msg


def _open_visa_OC(rm, visa_address):
    visa_inst = rm.open_resource(visa_address)
    visa_inst.parity = OC_parity  # = Parity.none
    visa_inst.baud_rate = OC_baud_rate  # = 19200
    visa_inst.data_bits = OC_data_bits  # = 8
    visa_inst.read_termination = OC_read_termination  # = '\r'
    visa_inst.flow_control = OC_flow_control  # = 0
    visa_inst.timeout = OC_timeout  # = 10000
    visa_inst.clear()
    return visa_inst


def _check_OC(rm, visa_address, n_tries_max=5):
    n_tries = 0
    success = False
    version = False
    while not(success) and (n_tries < n_tries_max):
        try:
            visa_inst = _open_visa_OC(rm, visa_address)
            output_raw = visa_inst.query('\X01J00\X00\XCB')
            visa_inst.close()
            success = True
            vals = output_raw[5:-3].split(';')
            status_dict = dict(zip(OC_status_keys, vals))
            version = status_dict['version']
        except:
            pass
        n_tries = n_tries + 1
    return version


def list_instruments():
    instruments = []
    visa_list = rm.list_resources()
    for addr in visa_list:
        if addr[0:4] == 'ASRL':
            version = _check_OC(rm, addr)
            if version:
                params = ParamSet(CovesionOC, visa_address=addr)
                instruments.append(params)
    return instruments


class CovesionOC(TempController):
    """Class definition for a Covesion OC1 and OC2 oven temperature controllers."""

    def _initialize(self):
        self.visa_address = self._paramset['visa_address']
        self.parity = OC_parity
        self.baud_rate = OC_baud_rate
        self.data_bits = OC_data_bits
        self.read_termination = OC_read_termination
        self.flow_control = OC_flow_control
        self.timeout = OC_timeout
        self.status_keys = OC_status_keys
        self.drive_str = '\x01m041;0;A9'

    def open_visa(self):
        """Helper function to open a visa connection to a Covesion OC. Used by
        other CovesionOC methods. Returns an active visa resource instance
        connected to the Covesion OC.
        """
        visa_inst = rm.open_resource(self.visa_address)
        visa_inst.parity = self.parity  # = Parity.none
        visa_inst.baud_rate = self.baud_rate  # = 19200
        visa_inst.data_bits = self.data_bits  # = 8
        visa_inst.read_termination = self.read_termination  # = '\r'
        visa_inst.flow_control = self.flow_control  # = 0
        visa_inst.timeout = self.timeout  # = 10000
        visa_inst.clear()
        return visa_inst

    def get_status(self, n_tries_max=50):
        """Collect and return status information from Covesion OC. Status values are returned in a
        dictionary with keys 'set point','temperature', 'control','output %','alarms','faults','temp
        ok','supply vdc','version', 'test cycle' and 'test mode'.

        Parameters
        ----------
        n_tries_max : int, optional
            number of times to try collecting status before throwing an error.
            This was added because this communication randomly fails sometimes.
        """
        n_tries = 0
        success = False
        while not(success) and (n_tries < n_tries_max):
            try:
                visa_inst = self.open_visa()
                output_raw = visa_inst.query('\X01J00\X00\XCB')
                visa_inst.close()
                success = True
            except:
                pass
            n_tries = n_tries + 1
        vals = output_raw[5:-3].split(';')
        return dict(zip(self.status_keys, vals))

    def get_current_temp(self, n_tries_max=20):
        """Collect and return current temperature from Covesion OC. The current
        temperature is returned as a Pint quantity in degrees C.

         Parameters
         ----------
         n_tries_max : int, optional
             number of times to try collecting status before throwing an error.
             This was added because this communication randomly fails sometimes.
         """
        n_tries = 0
        while (n_tries < n_tries_max):
            try:
                return Q_(float(self.get_status()['temperature']), u.degC)
            except:
                sleep(0.5)
                n_tries += 1

    def get_set_temp(self, n_tries_max=20):
        """Collect and return set temperature from Covesion OC. The set
        temperature is returned as a Pint quantity in degrees C.

         Parameters
         ----------
         n_tries_max : int, optional
             number of times to try collecting status before throwing an error.
             This was added because this communication randomly fails sometimes.
         """
        n_tries = 0
        while (n_tries < n_tries_max):
            try:
                return Q_(float(self.get_status()['set point']), u.degC)
            except:
                sleep(0.5)
                n_tries += 1

    def _set_set_temp(self, set_temp):
        """Helper function to set the 'set temperature' of a Covesion OC to a
        specified value. Used by the set_set_temp method, which does the same
        thing with extra code to prevent large, rapid temperature changes which
        can lead to crystal damage.

         Parameters
         ----------
         set_temp : Pint Quantity
             Set temperature to be sent to Covesion OC. Should be provided in
             degC units.
         """
        set_temp_degC = set_temp.m_as('degC')
        if Q_(20, u.degC) < set_temp <= Q_(200, u.degC):
            if set_temp < Q_(100, u.degC):
                cmd_str = '\x01i371;{:.3f};25.000;0.000;25;100.00;0.00;'.format(set_temp_degC)
            else:
                cmd_str = '\x01i381;{:.3f};25.000;0.000;25;100.00;0.00;'.format(set_temp_degC)
            checksum_str = format(sum(ord(ch) for ch in cmd_str) % 256, 'x')
            cmd_str += checksum_str
            visa_inst = self.open_visa()
            visa_inst.visalib.set_buffer(visa_inst.session, 48, 100)
            visa_inst.flush(16)
            visa_inst.write_raw(cmd_str)
            visa_inst.write_raw(self.drive_str)
            visa_inst.close()
        else:
            raise Exception('set_temp input not in valid range (20-200C)')
        return

    def set_set_temp(self, set_temp):
        """Method to set the 'set temperature' of a Covesion OC to a specified
        value. If the new set temperature is more than 10 degrees C away from
        the current oven temperature, this function breaks the temperature
        setting change up into a sequence of 10 degree C increments, which are
        sent to the oven 1 minute apart. This is to avoid temperature change
        rates greater than 10 degrees C per minute, which according to Covesion
        can lead to crystal damage.

         Parameters
         ----------
         set_temp : Pint Quantity
             Set temperature to be sent to Covesion OC. Should be provided in
             degC units.
         """
        current_temp = self.get_current_temp()
        print('current_temp: {}'.format(current_temp))
        print('set_temp: {}'.format(set_temp))
        delta_temp_degC = np.abs(set_temp - current_temp).m_as('degC')
        if delta_temp_degC > 10:
            n_comm = round(delta_temp_degC/10) + 1
            T_comm = np.linspace(current_temp.m_as('degC'),
                                 set_temp.m_as('degC'),
                                 n_comm+1)
            T_step = T_comm[1] - T_comm[0]
            # number of seconds to wait between steps, targeting ~10C/min
            t_step = abs(T_step / 10.0 * 60)
            T_comm = Q_(T_comm[1:], u.degC)
            for Tind, TT in enumerate(T_comm):
                print_statusline('\rapproaching temp: {:3.2f}C from {:3.2f}C, step {} of {}...'.format(float(set_temp.m_as('degC')), float(current_temp.m_as('degC')), Tind+1, n_comm))
                self._set_set_temp(TT)
                sleep(t_step)
            return
        else:
            self._set_set_temp(set_temp)
            return

    def set_temp_and_wait(self, set_temp, max_err=Q_(0.1,u.degK), n_samples=10, timeout=5*u.minute):
        """Method to set the 'set temperature' of a Covesion OC to a specified
        value and then wait for that temperature to be reached to within a
        specified stability. The user provides a maximum temperature error and a
        number of temperature measurements (which occur at approximately
        1/second) to specify the stability.

        Parameters
        ----------
        set_temp : Pint Quantity
            Set temperature to be sent to Covesion OC. Should be provided in
            degC units.
        max_error : Pint Quantity, optional
            Maximum temperature error that can be recorded over n_samples
            current temperature checks such that the temperature is considered
            stable. Provided in units of degK
        n_samples : int, optional
            Number checks for which the current temperature must be found to
            be within max_error of set_temp so that the temperature is
            considered stable.
        timeout: Pint Quantity
            Time allowed to pass before the function gives up on waiting for
            temperature stability and returns. Can be provided in any
            units of time.
         """
        self.set_set_temp(set_temp)
        err = np.ones((n_samples)) * 10.0 * max_err
        t0 = time.time()
        while (err.m_as('degK') > max_err.m_as('degK')).any() and ((time.time()-t0) < timeout.m_as('s')):
            err[0:n_samples-1] = err[1:]
            current_error = (self.get_current_temp() - set_temp).to(u.degK)
            err[n_samples-1] = np.abs(current_error)
            print_statusline('\rapproaching temp: {:3.2f}C, current temp error: {:3.2f}, time elapsed: '.format(float(set_temp.m_as('degC')), float(current_error.magnitude)) + str(timedelta(seconds=int(time.time()-t0))))
        if (time.time()-t0) > timeout.m_as('s'):
            raise Exception('Timeout while waiting for Covesion OC1 to reach set temperature {:3.2f}C'.format(set_temp.m_as('degC')))
        else:
            print_statusline('temperature {:3.2f}C reached in {:3.1f}s'.format(set_temp.m_as('degC'), time.time()-t0))
        return
