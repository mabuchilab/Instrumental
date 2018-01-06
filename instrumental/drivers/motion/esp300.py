# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 15:33:34 2015

Copyright 2016 - Christopher Rogers
"""

import serial
import time
from enum import Enum
from . import Motion
from ..util import check_units, check_enums
from .. import _ParamDict
from ... import Q_
from ...errors import InstrumentTypeError


"""  Commands not implemented:
commands: QD
"""

def _instrument(params):
    """ Possible params include 'esp300_port'"""
    d = {}
    if 'esp300_port' in params:
        d['port'] = params['esp300_port']
    if not d:
        raise InstrumentTypeError()

    return ESP300(**d)

class ESP300:
    """ This class interfaces with the newport ESP300 motion controller
    """

    def __init__(self, port=0, timeout=10, wait=0.05):
        """ Connects to an ESP motion controller on port COMX, where X=port+1

        wait: time (in seconds) that the program waits to read in a response
        after sending a query

        port: integer which selects the COM port to connect through
        timeout: the timeout of reading from the serial connection (in seconds)
        """
        self._serial = serial.Serial(port, timeout=timeout)
        self._serial.setBaudrate(19200)
        self._serial.setRtsCts(True)
        self._wait = wait
        if timeout is None:
            self.timeout = 1e6
        else:
            self.timeout = timeout

    def _send_command_string(self, string, nmax=10):
        if string[-1] != '\r':
            string = string + '\r'
        nbits = len(string)
        nbits_written = 0
        i = 0
        while nbits_written != nbits:
            self._serial.flushInput()
            self._serial.flushOutput()
            nbits_written = self._serial.write(string)
            i = i + 1
            if i >= nmax:
                err_str = "Command '{}' was not sent properly".format(string)
                raise esp300Error(err_str)

    def _read_line(self, wait=None):
        if wait is None:
            wait = self._wait
        terminated = False
        read_string = ''
        time0 = time.time()
        while not terminated:
            bits_waiting = self._serial.inWaiting()
            temp_st = self._serial.read(bits_waiting)
            read_string = read_string + temp_st
            if read_string != '':
                if read_string[-1] == '\n':
                    terminated = True
            if not terminated:
                time.sleep(wait)
            if (time.time() - time0) > self.timeout:
                error_string = 'No line was available to be read'
                error_string = error_string + ' within the timetout'
                raise esp300Error(error_string)
        return read_string

    def _read_output(self, wait=None):
        line = self._read_line(wait)
        return line[0:-2]

    def _getset_command(self, command, axis, parameter, param_units=None,
                        param_type=None):
        print "parameter is {}".format(parameter)
        if not isinstance(axis, int):
            raise esp300Error('axis must be of type int')
        if parameter is not None:
            if param_units is not None:
                parameter = Q_(parameter).to(param_units).magnitude
            if param_type is not None:
                parameter = param_type(parameter)
        else:
            parameter = '?'
        command = '{}{}{}\r'.format(axis, command, parameter)
        print "command is {}".format(command)
        self._send_command_string(command)

        if parameter == '?':
            return_val = self._read_output()
            if param_units is not None:
                return_val = Q_(return_val + param_units)
            return return_val

    def getset_motor_current(self, axis, motor_current=None):
        return self._getset_command('QI', axis, motor_current,
                                    param_units='A')

    def getset_motor_average_voltage(self, axis,  motor_average_voltage=None):
        return self._getset_command('QV', axis, motor_average_voltage,
                                    param_units='V')

    def getset_tachometer_gain(self, axis, tachometer_gain=None):
        return self._getset_command('QT', axis, tachometer_gain,
                                    param_units='V/krpm')

    def getset_motor_type(self, axis, motor_type=None):
        return self._getset_command('QM', axis, motor_type, param_type=int)

    def getset_microstep_factor(self, axis, microstep_factor=None):
        return self._getset_command('QS', axis, microstep_factor,
                                    param_units=int)

    def getset_gear_constant(self, axis, gear_constant=None):
        return self._getset_command('QG', axis, gear_constant,
                                    param_type=float)

    def update_motor_driver_settings(self, axis):
        return self._getset_command('QD', axis, '')

    def getset_emergency_decel(self, axis, emergency_decel=None):
        return self._getset_command('AE', axis, emergency_decel,
                                    param_units=' 1/s^2', param_type=int)

    def getset_accel_ffg(self, axis, accel_ffg=None):
        return self._getset_command('AF', axis, accel_ffg,
                                    param_type=float)

    def getset_max_accel(self, axis, max_accel=None):
        return self._getset_command('AU', axis, max_accel,
                                    param_units=' 1/s^2', param_type=float)

    def getset_accel(self, axis, accel=None):
        return self._getset_command('AC', axis, accel,
                                    param_units=' 1/s^2', param_type=float)

    def getset_decel(self, axis, decel=None):
        return self._getset_command('AG', axis, decel,
                                    param_units=' 1/s^2', param_type=float)

    def getset_backlash_compensation(self, axis, backlash_compensation=None):
        return self._getset_command('BA', axis, backlash_compensation,
                                    param_type=int)

    def getset_linear_compensation(self, axis, linear_compensation=None):
        return self._getset_command('CO', axis, linear_compensation,
                                    param_type=int)

    def getset_closed_loop_update(self, axis, closed_loop_update=None):
        return self._getset_command('CL', axis, closed_loop_update,
                                    param_units='ms', param_type=int)

    def getset_position_deadband(self, axis, position_deadband=None):
        return self._getset_command('DB', axis, position_deadband,
                                    param_type=int)

    def getset_max_follow_error(self, axis, max_follow_error=None):
        return self._getset_command('FE', axis, max_follow_error,
                                    param_type=float)

    def getset_encoder_full_step_resolution(self, axis,
                                            encoder_full_step_resolution=None):
        return self._getset_command('FR', axis, encoder_full_step_resolution,
                                    param_type=float)

    def getset_MS_reduction_ratio(self, axis, MS_reduction_ratio=None):
        return self._getset_command('GR', axis, MS_reduction_ratio,
                                    param_type=float)

    def getset_jog_high_speed(self, axis, jog_high_speed=None):
        return self._getset_command('JH', axis, jog_high_speed,
                                    param_units=' 1/s', param_type=float)

    def getset_jog_low_speed(self, axis, jog_low_speed=None):
        return self._getset_command('JW', axis, jog_low_speed,
                                    param_units=' 1/s', param_type=float)

    def getset_jerk_rate(self, axis, jerk_rate=None):
        return self._getset_command('JK', axis, jerk_rate,
                                    param_units=' 1/s^3', param_type=float)

    def getset_derivative_gain(self, axis, derivative_gain=None):
        return self._getset_command('KD', axis, derivative_gain,
                                    param_type=float)

    def getset_integral_gain(self, axis, integral_gain=None):
        return self._getset_command('KI', axis, integral_gain,
                                    param_type=float)

    def getset_proportional_gain(self, axis, proportional_gain=None):
        return self._getset_command('KP', axis, proportional_gain,
                                    param_type=float)

    def getset_saturation_level_of_IF(self, axis, saturation_level_of_IF=None):
        return self._getset_command('KS', axis, saturation_level_of_IF,
                                    param_type=float)

    def getset_home_search_high_speed(self, axis, home_search_high_speed=None):
        return self._getset_command('OH', axis, home_search_high_speed,
                                    param_units=' 1/s', param_type=float)

    def getset_home_search_low_speed(self, axis, home_search_low_speed=None):
        return self._getset_command('OL', axis, home_search_low_speed,
                                    param_units=' 1/s', param_type=float)

    def getset_home_search_mode(self, axis, home_search_mode=None):
        return self._getset_command('OM', axis, home_search_mode,
                                    param_type=int)

    def getset_home_preset_position(self, axis, home_preset_position=None):
        return self._getset_command('SH', axis, home_preset_position,
                                    param_type=float)

    def getset_MS_jog_velocity_update(self, axis, MS_jog_velocity_update=None):
        return self._getset_command('SI', axis, MS_jog_velocity_update,
                                    param_units=' ms', param_type=int)

    def getset_MS_jog_velocity_scaling(self, axis,
                                       MS_jog_velocity_scaling=None):
        MS_jog_velocity_scaling = '{},{}'.format(MS_jog_velocity_scaling[0],
                                                 MS_jog_velocity_scaling[1])
        return self._getset_command('SK', axis, MS_jog_velocity_scaling)

    def getset_left_travel_limit(self, axis, left_travel_limit=None):
        return self._getset_command('SL', axis, left_travel_limit,
                                    param_type=float)

    def getset_axis_displacement_units(self, axis,
                                       axis_displacement_units=None):
        return self._getset_command('SN', axis, axis_displacement_units,
                                    param_type=int)

    def getset_right_travel_limit(self, axis, right_travel_limit=None):
        return self._getset_command('SR', axis, right_travel_limit,
                                    param_type=float)

    def getset_MS_relationship(self, axis_slave, axis_master=None):
        return self._getset_command('SS', axis_slave, axis_master,
                                    param_type=int)

    def getset_encoder_resolution(self, axis, encoder_resolution=None):
        return self._getset_command('SU', axis, encoder_resolution,
                                    param_type=float)

    def getset_velocity_ffg(self, axis, velocity_ffg=None):
        return self._getset_command('VF', axis, velocity_ffg,
                                    param_type=float)

    def getset_velocity(self, axis, velocity=None):
        return self._getset_command('VA', axis, velocity,
                                    param_units=' 1/s', param_type=float)

    def getset_maximum_velocity(self, axis, maximum_velocity=None):
        return self._getset_command('VU', axis, maximum_velocity,
                                    param_units=' 1/s', param_type=float)

    def getset_update_servo_filter(self, axis):
        return self._getset_command('UF', axis, '')

    def close(self):
        self._serial.close()


class esp300Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MOTOR_TYPE:
    def __init__(self):
        self.UNDEFINED = 0
        self.DC_SERVO = 1
        self.DIGITAL_STEP_MOTOR = 2
        self.ANALOG_STEP_MOTOR = 3
        self.COMMUTATED_BRUSHLESS_DC_SERVO = 4


class HOME_TYPE:
    def __init__(self):
        self.FIND_ZERO_POSITION_COUNT = 0
        self.FIND_HOME_AND_INDEX_SIGNALS = 1
        self.FIND_HOME_SIGNAL = 2
        self.FIND_POSITIVE_LIMIT_SIGNAL = 3
        self.FIND_NEGATIVE_LIMIT_SIGNAL = 4
        self.FIND_POS_LIM_AND_INDEX_SIGNALS = 5
        self.FIND_NEG_LIM_AND_INDEX_SIGNALS = 6


class UNIT_TYPE:
    def __init__(self):
        self.ENCODER_COUNT = 0
        self.MOTOR_STEP = 1
        self.MILLIMETER = 2
        self.MICROMETER = 3
        self.INCH = 4
        self.MILLIINCH = 5
        self.MICROINCH = 6
        self.DEGREE = 7
        self.GRADIENT = 8
        self.RADIAN = 9
        self.MILLIRADIAN = 10
        self.MICRORADIAN = 11