# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Dodd Gray, and Nate Bogdanowicz
"""
Driver for controling Standa stepper motors using the MicroSMC (USMC) Driver
"""
from __future__ import division
import logging as log
from enum import Enum
from nicelib import NiceLib, NiceObjectDef, load_lib
from time import sleep
from . import Motion
from .. import _ParamDict
from ..util import check_units
from ... import u, Q_
from ...errors import InstrumentTypeError

__all__ = ['USMCDLL']

# Developed using version 2.1.0.29 of pf_cam.dll
info = load_lib('USMCDLL', __package__)
ffi = info._ffi

# _dev_list = NiceUSMC.Init()
# n_devs = int(_dev_list.NOD) # number of USMC devices seen by the driver
# dev_list = [{'dev_num':dev_ind,
#             'serial':ffi.string(ffi.unpack(_dev_list.Serial,n_devs)[dev_ind]),
#             'driver_version':ffi.string(ffi.unpack(_dev_list.Version,n_devs)[dev_ind]),} for dev_ind in range(n_devs)]

class USMC_Exception(Exception):
    """Base exception class for USMC errors"""
    pass


class NiceUSMC(NiceLib):
    _info = info
    _prefix = 'USMC_'
    _ret = 'err_check'

    def _ret_err_check(retval):
        if retval != 0:
            raise USMC_Exception(NiceUSMC.GetLastErr())

    Init = ('out')
    Close = ()
    GetLastErr = ('buf','len',{'ret': 'ignore'})

    Device = NiceObjectDef(attrs=dict(
        GetState = ('in','out'),
        SaveParametersToFlash = ('in'),
        SetCurrentPosition = ('in','in'),
        GetMode = ('in','out'),
        SetMode = ('in','inout'),
        GetParameters = ('in','out'),
        SetParameters = ('in','inout'),
        GetStartParameters = ('in','out'),
        Start = ('in', 'in', 'inout','out'),
        Stop = ('in'),
        GetEncoderState = ('in','inout')
    ))

class USMC(Motion):
        """ Class for controlling Standa stepper motor microcontroller boards
        using the MicroSMC (USMC) driver.
        """
        # self._lib = NiceUSMC

        def __init__(self, dev_id, travel_per_step):
            """
            Parameters
            ----------
            int dev_num: integer specifying device ID number as reported by NiceUSMC.Init()
            travel_per_step: pint quantity specifying distance traveled each step
                                   Note that Standa cites motor's resolution, refering to
                                   the travel per step divided by the maximum step divider
                                   (often 8). eg. for the 8CMA06 stepper motor,
                                   the resolution is 156nm for 1/8 step travel,
                                   so the step size is 8 * 156nm = 1.248um)
            """
            self._dev = NiceUSMC.Device(dev_id)
            self.dev_id = dev_id
            self.serial = dev_list[dev_id]['serial']
            self.driver_version = dev_list[dev_id]['driver_version']
            self._start_params = self._dev.GetStartParameters()
            self.step_divisor = int(self._start_params.SDivisor)
            self.mode = self._dev.GetMode()
            self.power = not(self.mode.ResetD)
            self.units = u.mm               # default posotion units
            self.calibration = False        # True when motor postion relative
                                            # to limit switches has been calibrated
                                            # initialize as False
            self.limit_switch_1_pos = False
            self.limit_switch_2_pos = False
            self.travel_per_step = travel_per_step.to(self.units)
            self.travel_per_microstep = self.travel_per_step / self.step_divisor

        def _state(self):
            return self._dev.GetState()

        def get_current_position(self,unitful=True):
            """Function to return current position. The driver board returns
            postion in "encoder units", which correspond to the stepper motor's
            step size divided by the "step divisor" which is a setting that usually
            can be 1, 2, 4 or 8 and can be queried using self._start_params.SDivisor.
            Using the motor resolution spec from Standa, these can be converted
            to unitful postions. This function takes a units argrument. If
            units=None, the position is returned in encoder units.
            """
            pos_enc = self._state().CurPos
            if unitful:
                if self.calibration:
                    pos = ((pos_enc - self.limit_switch_1_pos) * self.travel_per_microstep).to(self.units)
                    return pos
                else:
                    raise USMC_Exception('Cannot provide unitful position because limit switch calibration has not been run. Current encoder value is {}'.format(self.get_current_position(unitful=False)))
            else:
                return self._state().CurPos

        def get_voltage(self):
            """Function to return motor power supply voltage."""
            return self._state().Voltage

        def get_temperature(self):
            """Function to return motor temperature."""
            return Q_(self._state().Temp, u.degC)

        def get_power(self):
            """Function to return boolean indicating whether motor is powered"""
            return self._state().Power

        def get_running(self):
            """Function to return boolean indicating whether motor is rotating"""
            return self._state().RUN

        def get_limit_switch_1(self):
            """Function to return boolean indicating whether limit switch 1
            is pressed."""
            return not(self._state().Trailer1)

        def get_limit_switch_2(self):
            """Function to return boolean indicating whether limit switch 2
            is pressed."""
            return not(self._state().Trailer2)

        def go(self,pos,speed=5000,ls_override=False):
            """Function to move stepper motor to desired position at a given speed.

            Parameters:
            pos: target position [either integer in motor encoder units or pint length quantity]
            float speed: max motor speed to be used while moving to pos [(steps / step_divisor) / second]
            ls_override: boolean, if true commands to move beyond limit switch positions are allowed
            """
            if type(pos)==type(3*u.mm):
                if self.calibration:
                    pos_enc = int((pos / self.travel_per_microstep ).to(u.dimensionless).magnitude) + self.limit_switch_1_pos
                else:
                    raise USMC_Exception('Cannot move to unitful target position because calibration has not been run')
            else:
                pos_enc = int(pos)

            if not ls_override:
                if pos_enc < self.limit_switch_1_pos:
                    raise USMC_Exception('Cannot move to target position {:3.3g} because it is below the lower-limit limit switch'.format(pos))

                if pos_enc > self.limit_switch_2_pos:
                    raise USMC_Exception('Cannot move to target position {:3.3g} because it is beyond the upper-limit limit switch'.format(pos))

            if self.get_power():
                self._dev.Start(pos_enc,speed)
            else:
                raise USMC_Exception('Motor currently off. Cannot move.')

        def power_on(self):
            """Function to turn the motor power on."""
            mode = self._dev.GetMode()
            mode.ResetD = 0
            self.mode = self._dev.SetMode(mode)

        def power_off(self):
            """Function to turn the motor power on."""
            mode = self._dev.GetMode()
            mode.ResetD = 1
            self.mode = self._dev.SetMode(mode)

        def get_power(self):
            """Function to check if the motor power on."""
            self.mode = self._dev.GetMode()
            self.power = not(self.mode.ResetD)
            return self.power

        def find_limit_switch_1(self,speed=3000,polling_period=5*u.millisecond):
            """Function to move motor to limit swtich 1 position"""
            self.power_on()
            self.go(-50000,speed=speed,ls_override=True)
            print('moving toward limit switch 1...')
            while not(self.get_limit_switch_1()):
                sleep(polling_period.to(u.second).magnitude)
            self._dev.Stop()
            print('found limit switch 1 at encoder position {}'.format(self.get_current_position(unitful=False)))
            return self.get_current_position(unitful=False)

        def find_limit_switch_2(self,speed=3000,polling_period=5*u.millisecond):
            """Function to move motor to limit swtich 1 position"""
            self.power_on()
            self.go(50000,speed=speed,ls_override=True)
            print('moving toward limit switch 2...')
            while not(self.get_limit_switch_2()):
                sleep(polling_period.to(u.second).magnitude)
            self._dev.Stop()
            print('found limit switch 2 at position {}'.format(self.get_current_position(unitful=False)))
            return self.get_current_position(unitful=False)

        def initialize_calibration(self):
            """Function to find limit switch position values. This information
            can be used in combination with the stage travel specs to
            allow for measurement and control of the stage in real units.
            """
            init_pos = self.get_current_position(unitful=False)
            self.limit_switch_1_pos = self.find_limit_switch_1()
            self.limit_switch_2_pos = self.find_limit_switch_2()
            self.calibration = True
            print('limit switches found. moving back to initial position...')
            self.go(init_pos)                   # return to initial position



_dev_list = NiceUSMC.Init()
n_devs = int(_dev_list.NOD) # number of USMC devices seen by the driver
dev_list = [{'dev_num':dev_ind,
            'serial':ffi.string(ffi.unpack(_dev_list.Serial,n_devs)[dev_ind]),
            'driver_version':ffi.string(ffi.unpack(_dev_list.Version,n_devs)[dev_ind]),} for dev_ind in range(n_devs)]

        #     self._unit_scaling = (gear_box_ratio * micro_steps_per_step *
        #                           steps_per_rev / (360.0 * u.deg))
        #     self._open()
        #     self._start_polling(polling_period)
        #     self._wait_for_message(0, 0)  # Make sure status has been loaded before we return
        #
        # @property
        # def _param_dict(self):
        #     param_dict = _ParamDict(self.__class__.__name__)
        #     param_dict['module'] = 'motion.kinesis'
        #     param_dict['kinesis_serial'] = self.serial
        #     param_dict['offset'] = str(self.offset)
        #     return param_dict
        #
        # def _open(self):
        #     NiceKinesisISC.BuildDeviceList()  # Necessary?
        #     self.dev = NiceKinesisISC.Device(self.serial)
        #     self.dev.Open()
        #
        # def close(self):
        #     self.dev.StopPolling()
        #     self.dev.Close()
        #
        # @check_units(polling_period='ms')
        # def _start_polling(self, polling_period='200ms'):
        #     """Starts polling the device to update its status with the given period provided, rounded
        #     to the nearest millisecond
        #
        #     Parameters
        #     ----------
        #     polling_period: pint quantity with units of time
        #     """
        #     self.polling_period = polling_period
        #     self.dev.StartPolling(self.polling_period.m_as('ms'))
        #
        # @check_units(angle='deg')
        # def move_to(self, angle, wait=False):
        #     """Rotate the stage to the given angle
        #
        #     Parameters
        #     ----------
        #     angle : Quantity
        #         Angle that the stage will rotate to. Takes the stage offset into account.
        #     """
        #     log.debug("Moving stage to {}".format(angle))
        #     log.debug("Current position is {}".format(self.position))
        #     self.dev.ClearMessageQueue()
        #     self.dev.MoveToPosition(self._to_dev_units(angle + self.offset))
        #     if wait:
        #         self.wait_for_move()
        #
        # def _wait_for_message(self, match_type, match_id):
        #     msg_type, msg_id, msg_data = self.dev.WaitForMessage()
        #     log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))
        #     while msg_type != match_type or msg_id != match_id:
        #         msg_type, msg_id, msg_data = self.dev.WaitForMessage()
        #         log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))
        #
        # def _check_for_message(self, match_type, match_id):
        #     """Check if a message of the given type and id is in the queue"""
        #     while True:
        #         try:
        #             msg_type, msg_id, msg_data = self.dev.GetNextMessage()
        #         except KinesisError:
        #             return False
        #
        #         log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))
        #         if msg_type == match_type and msg_id == match_id:
        #             return True
        #
        # def wait_for_move(self):
        #     """Wait for the most recent move to complete"""
        #     self._wait_for_message(2, 1)
        #
        # def move_finished(self):
        #     """Check if the most recent move has finished"""
        #     return self._check_for_message(2, 1)
        #
        # def _to_real_units(self, dev_units):
        #     return (dev_units / self._unit_scaling).to('deg')
        #
        # @check_units(real_units='deg')
        # def _to_dev_units(self, real_units):
        #     return int(round(float(real_units * self._unit_scaling)))
        #
        # def home(self, wait=False):
        #     """Home the stage
        #
        #     Parameters
        #     ----------
        #     wait : bool, optional
        #         Wait until the stage has finished homing to return
        #     """
        #     self.dev.ClearMessageQueue()
        #     self.dev.Home()
        #
        #     if wait:
        #         self.wait_for_home()
        #
        # def wait_for_home(self):
        #     """Wait for the most recent homing operation to complete"""
        #     self._wait_for_message(2, 0)
        #
        # def homing_finished(self):
        #     """Check if the most recent homing operation has finished"""
        #     return self._check_for_message(2, 0)
        #
        # @property
        # def needs_homing(self):
        #     """True if the device needs to be homed before a move can be performed"""
        #     return bool(self.dev.NeedsHoming())
        #
        # @property
        # def offset(self):
        #     return self._offset
        #
        # @offset.setter
        # @check_units(offset='deg')
        # def offset(self, offset):
        #     self._offset = offset
        #
        # @property
        # def position(self):
        #     return self._to_real_units(self.dev.GetPosition()) - self.offset
        #
        # @property
        # def is_homing(self):
        #     return bool(self.dev.GetStatusBits() & 0x00000200)
        #
        # @property
        # def is_moving(self):
        #     return bool(self.dev.GetStatusBits() & 0x00000030)
