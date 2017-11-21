# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Dodd Gray, and Nate Bogdanowicz
"""
Driver for controling Standa stepper motors using the MicroSMC (USMC) Driver
"""
from __future__ import division
import logging as log
from enum import Enum
from nicelib import NiceLib, NiceObjectDef, load_lib
from time import sleep, time
from . import Motion
from .. import _ParamDict
from ..util import check_units
from ... import u, Q_
from ...errors import InstrumentTypeError

__all__ = ['USMC']

# Developed using version 2.1.0.29 of pf_cam.dll
info = load_lib('USMC', __package__)
ffi = info._ffi

# _dev_list = NiceUSMC.Init()
# n_devs = int(_dev_list.NOD) # number of USMC devices seen by the driver
# dev_list = [{'dev_num':dev_ind,
#             'serial':ffi.string(ffi.unpack(_dev_list.Serial,n_devs)[dev_ind]),
#             'driver_version':ffi.string(ffi.unpack(_dev_list.Version,n_devs)[dev_ind]),} for dev_ind in range(n_devs)]

class USMC_Exception(Exception):
    """Base exception class for USMC errors. Stops motor motion and reports position."""
    def __init__(self,msg,motor=None,stop=True):
        if stop:
            motor.stop()
            pos = motor.get_current_position()
            serial = motor.serial
            stop_msg = 'USMC board with serial ' + serial + ' stopped with motor at position {}'.format(pos)
            msg = msg + '\n' + stop_msg
        super(self.__class__,self).__init__(msg)




class NiceUSMC(NiceLib):
    _info = info
    _prefix = 'USMC_'
    _ret = 'err_check'

    def _ret_err_check(retval):
        if retval != 0:
            raise USMC_Exception(NiceUSMC.GetLastErr(),stop=False)

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

        def __init__(self, dev_id, travel_per_step=None, step_divisor=None, travel_per_microstep=None):
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
            self.step_divisor = step_divisor
            #self._start_params = self._dev.GetStartParameters()
            #self.step_divisor = int(self._start_params.SDivisor)
            #print('step_divisor={}'.format(self.step_divisor))
            self.mode = self._dev.GetMode()
            self.power = not(self.mode.ResetD)
            self.units = u.mm               # default posotion units
            self.calibration = False        # True when motor postion relative
                                            # to limit switches has been calibrated
                                            # initialize as False
            self.limit_switch_1_pos = False
            self.limit_switch_2_pos = False
            if travel_per_step and not travel_per_microstep:
                self.travel_per_step = travel_per_step.to(self.units)
                self.travel_per_microstep = self.travel_per_step / self.step_divisor
            elif travel_per_microstep and not travel_per_step:
                self.travel_per_microstep = travel_per_microstep.to(self.units)
                self.travel_per_step = self.travel_per_microstep * self.step_divisor
            elif travel_per_microstep and travel_per_step:
                raise USMC_Exception('USMC initialization attempted supplying both travel_per_step and travel_per_microstep. Please supply only one or the other.',stop=False)
            else:
                raise USMC_Exception('USMC initialization attempted without supplying either travel_per_step or travel_per_microstep parameter. Please supply one or the other for motor position calibration.',stop=False)

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
                    raise USMC_Exception('Cannot provide unitful position because limit switch calibration has not been run. Current encoder value is {}'.format(self.get_current_position(unitful=False)),stop=False)
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
                    raise USMC_Exception('Cannot move to unitful target position because calibration has not been run',stop=False)
            else:
                pos_enc = int(pos)

            if not ls_override:
                if pos_enc < self.limit_switch_1_pos:
                    raise USMC_Exception('Cannot move to target position {:3.3g} because it is below the lower-limit limit switch'.format(pos),stop=False)

                if pos_enc > self.limit_switch_2_pos:
                    raise USMC_Exception('Cannot move to target position {:3.3g} because it is beyond the upper-limit limit switch'.format(pos),stop=False)

            if self.get_power():
                self._dev.Start(pos_enc,speed)
            else:
                raise USMC_Exception('Motor currently off. Cannot move.',stop=False)

        def wait_for_move(self,pos,verbose=False,polling_period=5*u.ms,unitful=True):
            if unitful:
                close_enough = 2*self.travel_per_microstep
            else:
                close_enough = 2 # encoder ticks

            if self.get_running():
                t0 = time()
                sleep(polling_period.to(u.second).magnitude)
                while self.get_running():
                    if verbose:
                        print('t: {:3.3g} sec, pos: {:3.3g}'.format(time()-t0, self.get_current_position(unitful=unitful)))
                    sleep(polling_period.to(u.second).magnitude)
                if verbose:
                    print('move to pos = {:3.3g} complete after {:3.3g} sec'.format(self.get_current_position(unitful=unitful),time()-t0))
            elif (self.get_current_position(unitful=unitful) - pos) < close_enough:
                if verbose:
                    print('already at pos = {:3.3g}, no need to wait'.format(self.get_current_position(unitful=unitful)))
            else:
                raise USMC_Exception('wait_for_move called while not currently moving. Perhaps polling period is longer than travel time?',motor=self,stop=True)

        def go_and_wait(self,pos,speed=5000,ls_override=False,verbose=False,polling_period=5*u.ms,unitful=True):
            self.go(pos,speed=speed,ls_override=ls_override)
            sleep(polling_period.to(u.second).magnitude)
            self.wait_for_move(pos,verbose=verbose,polling_period=polling_period,unitful=unitful)

        def stop(self,verbose=False,unitful=True):
            self._dev.Stop()
            if verbose:
                print('USMC motor stopped at position {:3.3g}'.format(self.get_current_position()))

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
            return self.limit_switch_1_pos, self.limit_switch_2_pos

        def step_foreward(self):
            """Function to take one microstep forward (increase actuator length),
            thus creating the smallest possible change in that direction. This
            might be useful for software feedback loops.
            """
            self.go(self.get_current_position(unitful=False)+1)

        def step_backward(self):
            """Function to take one microstep forward (increase actuator length),
            thus creating the smallest possible change in that direction. This
            might be useful for software feedback loops.
            """
            self.go(self.get_current_position(unitful=False)-1)

_dev_list = NiceUSMC.Init()
n_devs = int(_dev_list.NOD) # number of USMC devices seen by the driver
dev_list = [{'dev_num':dev_ind,
            'serial':ffi.string(ffi.unpack(_dev_list.Serial,n_devs)[dev_ind]),
            'driver_version':ffi.string(ffi.unpack(_dev_list.Version,n_devs)[dev_ind]),} for dev_ind in range(n_devs)]

def list_instruments():
    instruments = []
    for dev in dev_list:
        params = _ParamDict("<Standa MicroSMC motor ID '{}'>".format(dev['dev_num']))
        params['smc_dev_num'] = dev['dev_num']
        params['module'] = 'motion.USMC'
        params['serial'] = dev['serial']
        params['driver_version'] = dev['driver_version']
        instruments.append(params)
    return instruments


def _instrument(params):
    if 'smc_dev_num' in params:
        if 'travel_per_step' in params:
            inst = USMC(params['smc_dev_num'],travel_per_step=params['travel_per_step'])
        elif 'travel_per_microstep' in params:
            inst = USMC(params['smc_dev_num'],travel_per_microstep=params['travel_per_microstep'])
        else:
            raise Exception('either travel_per_step or travel_per_microstep parameter must be supplied to initialize USMC instrument')
    else:
        raise InstrumentTypeError()
    return inst
