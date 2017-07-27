# -*- coding: utf-8 -*-
# Copyright 2014-2017 Chris Rogers, Nate Bogdanowicz
"""Driver module for Attocube stages.

Interfaces with the ECC100 controller, which has support for various stages:
    * ECS3030
    * ECS3040
    * ECS3050
    * ECS3060
    * ECS3070
    * ECS3080
    * ECS5050
    * ECGp5050
    * ECGt5050
    * ECR3030

Note that ecc.dll must be on the system path, and that this is a windows only
driver.
"""

from __future__ import print_function
import time
from enum import Enum
from ctypes import (c_int32, c_bool, byref, create_string_buffer,
                    Structure, POINTER, oledll)
from . import Motion
from .. import ParamSet
from ..util import check_units, check_enums
from ...errors import InstrumentNotFoundError
from ... import Q_

_INST_PARAMS = ['id']
_INST_CLASSES = ['ECC100']

# __all__ = ['LinearStage', 'Goniometer', 'RotationStage', 'ECC100']

lib = oledll.LoadLibrary('ecc.dll')
_err_map = {
    -1: 'Unspecified error.',
    1: 'Communication timeout.',
    2: 'No active connection to device.',
    3: 'Error in communication with driver.',
    7: 'Device is already in use.',
    9: 'Parameter out of range.',
    10: 'Feature only available in pro version.'
}


def list_instruments():
    _, info_list = check_for_devices()
    return [ParamSet(ECC100, id=info.id) for info in info_list]


def check_for_devices():
    """ Checks for devices, returns their info and how many there are.

    Returns
    -------
    num : int
        number of devices connected
    info : list of EccInfo
        info list. Each EccInfo object has the attributes 'id', and
        'locked'
    """
    info = POINTER(EccInfo)()
    num = lib.ECC_Check(byref(info))

    info_list = [info[i] for i in range(num)]
    return num, info_list

class EccInfo(Structure):
    _fields_ = [('id', c_int32), ('locked', c_bool)]


class Actor(Motion):
    def __init__(self, controller, axis):
        self._c = controller
        self.axis = axis
        self.name = self._c._getActorName(self.axis)
        self.type = self._c._getActorType(self.axis)
        self.enable()

    def __repr__(self):
        return "<{} {}, axis={}>".format(self.__class__.__name__, self.name,
                                         self.axis)

    def enable(self):
        """ Enables communication from the controller to the stage. """
        self._c._controlOutput(self.axis, enable=True, set=True)

    def disable(self):
        """ Disables communication from the controller to the stage. """
        self._c._controlOutput(self.axis, enable=False, set=True)

    def is_enabled(self):
        """ Returns whether communication to the stage is enabled. """
        return self._c._controlOutput(self.axis, set=False)

    def is_ref_position_valid(self):
        """ Returns whether the reference position is valid. """
        return self._c._getStatusReference(self.axis)

    @check_units(amplitude='mV')
    def set_amplitude(self, amplitude):
        """ Sets the amplitude of the actuator signal.

        This modifies the step size of the positioner.

        Parameters
        ----------
        amplitude : pint.Quantity
            amplitude of the actuator signal in volt-compatible units. The
            allowed range of inputs is from 0 V to 45 V.
        """
        amp_in_mV = int(Q_(amplitude).to('mV').magnitude)
        if not (0 <= amp_in_mV <= 45e3):
            raise Exception("Amplitude must be between 0 and 45 V")
        self._c._controlAmplitude(self.axis, amp_in_mV, set=True)

    def get_amplitude(self):
        """ Gets the amplitude of the actuator signal. """
        amp_in_mV = self._c._controlAmplitude(self.axis, set=False)
        return Q_(amp_in_mV, 'mV').to('V')

    @check_units(frequency='Hz')
    def set_frequency(self, frequency):
        """ Sets the frequency of the actuation voltage applied to the stage.

        The frequency is proportional to the travel speed of the positioner.

        Parameters
        ----------
        frequency : pint.Quantity
            frequency of the actuator signal in Hz-compatible units. The
            allowed range of inputs is from 1 Hz to 2 kHz.
        """
        freq_in_mHz = int(Q_(frequency).to('mHz').magnitude)
        if not (1e3 <= freq_in_mHz <= 2e6):
            raise Exception("Frequency must be between 1 Hz and 2 kHz")
        self._c._controlFrequency(self.axis, freq_in_mHz, set=True)

    def get_frequency(self):
        """ Gets the frequency of the actuator signal. """
        freq_in_mHz = self._c._controlFrequency(self.axis, set=False)
        return Q_(freq_in_mHz, 'mHz').to('Hz')

    def step_once(self, backward=False):
        """ Step once. """
        self._c._setSingleStep(self.axis, backward)

    def start_stepping(self, backward=False):
        """
        Step continously until stopped.

        This will stop any ongoing motion in the opposite direction.
        """
        if backward:
            self._c._controlContinuousBkwd(self.axis, enable=True, set=True)
        else:
            self._c._controlContinuousFwd(self.axis, enable=True, set=True)

    def stop_stepping(self):
        """ Stop any continuous stepping. """
        if self.is_stepping_backward():
            self._c._controlContinuousBkwd(self.axis, enable=False, set=True)
        elif self.is_stepping_forward():
            self._c._controlContinuousFwd(self.axis, enable=False, set=True)

    def is_stepping_backward(self):
        return self._c._controlContinuousBkwd(self.axis, set=False)

    def is_stepping_forward(self):
        return self._c._controlContinuousFwd(self.axis, set=False)

    def get_position(self):
        """ Returns the current postion"""
        pos = self._c._getPosition(self.axis)
        return Q_(pos, self._pos_units)

    def get_ref_position(self):
        """ Returns the current reference positoin"""
        pos = self._c._getReferencePosition(self.axis)
        return Q_(pos, self._pos_units)

    def enable_feedback(self, enable=True):
        """ Control the positioning feedback-control loop

        enable: bool, where False corresponds to OFF and True corresponds to ON
        """
        self._c._controlMove(self.axis, enable, set=True)

    @check_units(duration='s')
    def timed_move(self, direction, duration):
        """ Moves in the specified direction for the specified
        duration.

        direction: bool controlling the direciton of movement.  True
        corresponds to the positive direction for linear stages and the
        negative direction for goniometers

        duration: duration of motion, a pint quantity with units of time
        """
        self._c._setContinuous(self.axis, direction, control=True)
        time.sleep(duration.to('s').magnitude)
        self._c._setContinuous(self.axis, direction, control=False)

    def is_feedback_on(self):
        """ Indicates if the feedback-control loop is ON
        (True) or OFF (False)
        """
        enable = self._c._controlMove(self.axis, set=False)
        return enable

    def set_target(self, target):
        """ Sets the target position of the feedback control loop.

        target: target position, in nm for linear stages, in micro radians for
        goniometers
        """
        target = Q_(target)
        target_mag = target.to(self._pos_units).magnitude
        self._c._controlTargetPosition(self.axis, target_mag, set=True)

    def get_target(self):
        """ Returns the target position of the feedback control loop."""
        targetPosition = self._c._controlTargetPosition(self.axis, set=False)
        return Q_(targetPosition, self._pos_units)

    def move_to(self, pos, wait=False):
        """ Moves to a location using closed loop control. """
        pos = Q_(pos)
        self.set_target(pos)
        self.enable_feedback(True)

        if wait:
            self.wait_unitl_at_position()

    @check_units(update_interval='ms')
    def wait_until_at_position(self, update_interval='10 ms', delta_pos=None):
        """Waits to return until the actor is at the target position

        delta_pos is the margin within which the device is considered to be at
        the target position
        """
        at_target = self.at_target(delta_pos)
        while not at_target:
            time.sleep(update_interval.to('s').magnitude)
            at_target = self.at_target(delta_pos)
            if at_target:
                return

    def at_target(self, delta_pos=None):
        """ Indicates whether the stage is at the target position.

        delta_pos is the tolerance within which the stage is considered
        'at position'
        """
        if delta_pos is None:
            if self._actor_type==ActorType.LinearStage:
                delta_pos = Q_('1nm')
            if self._actor_type==Goniometer:
                delta_pos = Q_('1 urad')
        target = self.get_target()
        position = self.get_position()
        delta = target - position
        delta = delta.to(self._pos_units).magnitude
        if delta <= delta_pos.to(self._pos_units).magnitude:
            return True
        else:
            return False


class LinearStage(Actor):
    def __init__(self, device, axis):
        super(LinearStage, self).__init__(device, axis)
        self._pos_units = 'nm'
        self._actor_type = ActorType.LinearStage


class Goniometer(Actor):
    def __init__(self, device, axis):
        super(Goniometer, self).__init__(device, axis)
        self._pos_units = 'micro radians'
        self._actor_type = ActorType.Goniometer


class RotationStage(Actor):
    pass

class ActorType(Enum):
    LinearStage = 0
    Goniometer = 1
    RotationStage = 2


class Status(Enum):
    idle =0
    moving = 1
    pending = 2


class Axis(Enum):
    one = 0
    two = 1
    three = 2


class ECC100(Motion):
    """
    Interfaces with the Attocube ECC100 controller. Windows-only.
    """
    def __init__(self, paramset):
        """ Connects to the attocube controller.

        id is the id of the device to be connected to
        """

        self._lib = lib
        self.ActorType = ActorType
        self.Status = Status
        self.Axis = Axis

        num, info = self._Check()
        if num < 1:
            raise Exception("No Devices Detected")

        if 'id' not in paramset:
            # Attempt to connect to the first device
            self._dev_num = 0
        else:
            self._dev_num = self._get_dev_num_from_id(int(paramset['id']))
        self._Connect()
        self._load_actors()
        self._default_actors = self.actors

    def _handle_err(self, retval, message=None, func=None):
        """ Handles the error codes returned from the functions in ecc.dll. """
        if retval == 0:
            return
        lines = []

        if message:
            lines.append(message)
        if func:
            lines.append("Error returned by '{}'".format(func))
        lines.append(_err_map[retval])

        raise Exception("\n".join(lines))

    def _load_actors(self):
        self.actors = []
        for cur_axis in range(3):
            cur_axis = Axis(cur_axis)
            if self._getStatusConnected(cur_axis):
                actor_type = ActorType(self._getActorType(cur_axis))
                if actor_type == ActorType.LinearStage:
                    actor = LinearStage(self, cur_axis)
                elif actor_type == ActorType.Goniometer:
                    actor = Goniometer(self, cur_axis)
                else:
                    actor = Actor(self, cur_axis)
                self.actors.append(actor)

    def _get_dev_num_from_id(self, device_id):
        N, info_list = self._Check()
        for i in range(N):
            if info_list[i].id==device_id:
                return i
        err_string = 'No ecc100 device with id matching {} found'.format(device_id)
        raise InstrumentNotFoundError(err_string)

    def _Check(self):
        """ Checks for devices and returns their info and how many there are.

        Returns
        -------
        num : int
            number of devices connected
        info : list of EccInfo
            info list. Each EccInfo object has the attributes 'id', and
            'locked'
        """
        info = POINTER(EccInfo)()
        num = self._lib.ECC_Check(byref(info))

        info_list = [info[i] for i in range(num)]
        return num, info_list

    def close(self):
        """ Closes the connection to the controller. """
        ret = self._lib.ECC_Close(self._dev_handle)
        self._handle_err(ret, func="Close")

    def _Connect(self):
        """
        Attempts to open a connection to the controller.

        If successful, sets
        the device handle self._dev_handle. Reads from self._dev_num.
        """
        handle = c_int32()
        ret = self._lib.ECC_Connect(self._dev_num, byref(handle))
        self._handle_err(ret, func="Connect")
        self._dev_handle = handle.value

    @check_enums(axis=Axis)
    def _controlActorSelection(self, axis, actor=0, set=False):
        """
        Controls the 'actor' property of a particular axis (ex. ECS3030)

        Parameters
        ----------
        axis : instance of Axis
            axis of control
        actor : int
            actor id, 0..255
        """
        actor = c_int32(actor)
        ret = self._lib.ECC_controlActorSelection(self._dev_handle, axis.value,
                                                  byref(actor), set)
        self._handle_err(ret, func="controlActorSelection")
        return actor.value

    @check_units(amplitude='mV')
    @check_enums(axis=Axis)
    def _controlAmplitude(self, axis, amplitude='0 mV', set=False):
        """ Controls the applied voltage for the specified axis. """
        amplitude = c_int32(int(amplitude.to('mV').magnitude))
        ret = self._lib.ECC_controlAmplitude(self._dev_handle, axis.value,
                                             byref(amplitude), set)
        self._handle_err(ret, func="controlAmplitude")
        return Q_(amplitude.value, 'mV')

    @check_enums(axis=Axis)
    def _controlAutoReset(self, axis, enable=False, set=False):
        """ Controls the auto-reset setting. """
        enable = c_int32(enable)
        ret = self._lib.ECC_controlAutoReset(self._dev_handle, axis.value,
                                             byref(enable), set)
        self._handle_err(ret, func="controlAutoReset")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlContinuousBkwd(self, axis, enable=False, set=False):
        """ Controls continuous backward motion of the specified axis. """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlContinousBkwd(self._dev_handle, axis.value,
                                                 byref(enable), set)
        self._handle_err(ret, func="controlContinousBkwd")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlContinuousFwd(self, axis, enable=False, set=False):
        """ Controls continuous forward motion of the specified axis. """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlContinousFwd(self._dev_handle, axis.value,
                                                byref(enable), set)
        self._handle_err(ret, func="controlContinousFwd")
        return bool(enable.value)

    def _controlDeviceId(self, id=0, set=False):
        """ Controls the device identifier stored in the device flash. """
        id = c_int32(id)
        ret = self._lib.ECC_controlDeviceId(self._dev_handle, byref(id), set)
        self._handle_err(ret, func="controlDeviceId")
        return id.value

    @check_enums(axis=Axis)
    def _controlEotOutputDeactivate(self, axis, enable=False, set=False):
        """
        Controls whether the given axis should deactivate its output when end
        of travel (EOT) is reached.
        """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlEotOutputDeactive(self._dev_handle, axis.value,
                                                     byref(enable), set)
        self._handle_err(ret, func="controlEotOutputDeactivate")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlExtTrigger(self, axis, enable=False, set=False):
        """ Controls the input trigger for steps. """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlExtTrigger(self._dev_handle, axis.value,
                                              byref(enable), set)
        self._handle_err(ret, func="controlExtTrigger")
        return bool(enable.value)

    @check_enums(axis=Axis)
    @check_units(voltage='uV')
    def _controlFixOutputVoltage(self, axis, voltage='0 uV', set=False):
        """ Controls the DC level on the output in uV. """
        voltage = c_int32(int(voltage.to('uV').magnitude))
        ret = self._lib.ECC_controlFixOutputVoltage(self._dev_handle, axis.value,
                                                    byref(voltage), set)
        self._handle_err(ret, func="controlFixOutputVoltage")
        return Q_(voltage.value, 'uV')

    @check_enums(axis=Axis)
    @check_units(frequency='Hz')
    def _controlFrequency(self, axis, frequency='0 Hz', set=False):
        """ Control the frequency parameter.  """
        frequency = c_int32(int(frequency.to('mHz').magnitude))
        ret = self._lib.ECC_controlFrequency(self._dev_handle, axis.value,
                                             byref(frequency), set)
        self._handle_err(ret, func="controlFrequency")
        return Q_(frequency.value, 'mHz')

    @check_enums(axis=Axis)
    def _controlMove(self, axis, enable=False, set=False):
        """
        Controls the feedback-control loop used for positioning the specified
        axis.
        """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlMove(self._dev_handle, axis.value,
                                        byref(enable), set)
        self._handle_err(ret, func="controlMove")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlOutput(self, axis, enable=False, set=False):
        """ Controls the 'output' state of a specific axis. """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlOutput(self._dev_handle, axis.value,
                                          byref(enable), set)
        self._handle_err(ret, func="controlOutput")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlReferenceAutoUpdate(self, axis, enable=False, set=False):
        """ Controls the reference auto update setting. """
        enable = c_bool(enable)
        ret = self._lib.ECC_controlReferenceAutoUpdate(self._dev_handle, axis.value,
                                                       byref(enable), set)
        self._handle_err(ret, func="controlReferenceAutoUpdate")
        return bool(enable.value)

    @check_enums(axis=Axis)
    def _controlTargetPosition(self, axis, target=0, set=False):
        """ Control the target position of the feedback control loop. """
        target = c_int32(int(target))
        ret = self._lib.ECC_controlTargetPosition(self._dev_handle, axis.value,
                                                  byref(target), set)
        self._handle_err(ret, func="controlTargetPosition")
        return target.value

    @check_enums(axis=Axis)
    def _controlTargetRange(self, axis, target_range=0, set=False):
        """
        Control the range around the target position where the stage is
        considered to be at the target.
        """
        target_range = c_int32(int(target_range))
        ret = self._lib.ECC_controlTargetRange(self._dev_handle, axis.value,
                                               byref(target_range), set)
        self._handle_err(ret, func="controlTargetRange")
        return target_range.value

    @check_enums(axis=Axis)
    def _getActorName(self, axis):
        """ Returns the name of the 'actor' of the specified axis. """
        buf = create_string_buffer(20)
        ret = self._lib.ECC_getActorName(self._dev_handle, axis.value, buf)
        self._handle_err(ret, func="getActorName")
        return buf.value.strip()

    @check_enums(axis=Axis)
    def _getActorType(self, axis):
        """ Returns  an int corrsesponding to the type of actor associated with
        the specified axis.
        """
        _type = c_int32()
        ret = self._lib.ECC_getActorType(self._dev_handle, axis.value,
                                         byref(_type))
        self._handle_err(ret, func="getActorType")
        return ActorType(_type.value)

    def _getDeviceInfo(self):
        """
        Returns the device ID and a boolean that indicates whether or not the
        device is locked.
        """
        dev_id = c_int32(0)
        locked = c_bool(0)
        ret = self._lib.ECC_getDeviceInfo(self._dev_num, byref(dev_id),
                                          byref(locked))
        self._handle_err(ret, func="getDeviceInfo")
        return dev_id.value, locked.value

    @check_enums(axis=Axis)
    def _getPosition(self, axis):
        """
        Returns the position of the stage on the specifed axis (in nm for
        linear stages, micro radians for goniometers).
        """
        position = c_int32()
        ret = self._lib.ECC_getPosition(self._dev_handle, axis.value,
                                        byref(position))
        self._handle_err(ret, func="getPosition")
        return position.value

    @check_enums(axis=Axis)
    def _getReferencePosition(self, axis):
        """
        Returns the reference position of the stage on the specifed axis (in nm
        for linear stages, micro radians for goniometers).
        """
        reference = c_int32()
        ret = self._lib.ECC_getReferencePosition(self._dev_handle, axis.value,
                                                 byref(reference))
        self._handle_err(ret, func="getReferencePosition")
        return reference.value

    @check_enums(axis=Axis)
    def _getStatusConnected(self, axis):
        """ Returns whether actor given by `axis` is connected or not. """
        connected = c_int32()
        ret = self._lib.ECC_getStatusConnected(self._dev_handle, axis.value,
                                               byref(connected))
        self._handle_err(ret)
        return bool(connected.value)

    @check_enums(axis=Axis)
    def _getStatusEotBkwd(self, axis):
        """
        Returns whether the given axis is at the end of travel (EOT) in the
        backward direction.
        """
        at_eot = c_bool()
        ret = self._lib.ECC_getStatusEotBkwd(self._dev_handle, axis.value,
                                             byref(at_eot))
        self._handle_err(ret, func="getStatusEotBkwd")
        return bool(at_eot.value)

    @check_enums(axis=Axis)
    def _getStatusEotFwd(self, axis):
        """
        Returns whether the given axis is at the end of travel (EOT) in the
        forward direction.
        """
        at_eot = c_bool()
        ret = self._lib.ECC_getStatusEotFwd(self._dev_handle, axis.value,
                                            byref(at_eot))
        self._handle_err(ret, func="getStatusEotFwd")
        return bool(at_eot.value)

    @check_enums(axis=Axis)
    def _getStatusError(self, axis):
        """ Returns True if there is an error due to sensor malfunction. """
        has_err = c_bool()
        ret = self._lib.ECC_getStatusError(self._dev_handle, axis.value,
                                           byref(has_err))
        self._handle_err(ret, func="getStatusError")
        return bool(has_err.value)

    @check_enums(axis=Axis)
    def _getStatusFlash(self, axis):
        """ Returns whether the flash is being written to or not. """
        flash_is_writing = c_bool()
        ret = self._lib.ECC_getStatusFlash(self._dev_handle, axis.value,
                                           byref(flash_is_writing))
        self._handle_err(ret, func="getStatusFlash")
        return bool(flash_is_writing.value)

    @check_enums(axis=Axis)
    def _getStatusMoving(self, axis):
        """
        Returns whether the specified axis is idle, moving or pending.

        Returns
        -------
        instance of Status
        """
        moving = c_int32()
        ret = self._lib.ECC_getStatusMoving(self._dev_handle, axis.value,
                                            byref(moving))
        self._handle_err(ret, func="getStatusMoving")
        return Status(moving.value)

    @check_enums(axis=Axis)
    def _getStatusReference(self, axis):
        """ Checks whether or not the reference position is valid. """
        status = c_bool()
        ret = self._lib.ECC_getStatusReference(self._dev_handle, axis.value,
                                               byref(status))
        self._handle_err(ret, func="getStatusReference")
        return bool(status.value)

    @check_enums(axis=Axis)
    def _getStatusTargetRange(self, axis):
        """ Returns whether the stage is considered to be at its target. """
        at_target = c_bool()
        ret = self._lib.ECC_getStatusTargetRange(self._dev_handle, axis.value,
                                                 byref(at_target))
        self._handle_err(ret, func="getStatusTargetRange")
        return bool(at_target.value)

    @check_enums(axis=Axis)
    def _setReset(self, axis):
        """ Resets the reference position to the current position.  """
        ret = self._lib.ECC_setReset(self._dev_handle, axis.value)
        self._handle_err(ret, func="resetReference")

    @check_enums(axis=Axis)
    def _setSingleStep(self, axis, backward):
        """ Causes the stage along the specified axis to take a single 'step'

        direction = 0 -> positive movement for linear stages, and negative
        movement for goniometers

        direction = 1 -> negative movement for linear stages, and positive
        movement for goniometers
        """
        ret = self._lib.ECC_setSingleStep(self._dev_handle, axis.value,
                                          backward)
        self._handle_err(ret, func="setSingleStep")

    # As-yet unconverted functions below here

    @check_enums(axis=Axis)
    def _set_actor(self, axis, actor_id):
        """ Sets the 'actor' property of the specified axis

        Parameters
        ----------
        actor:  int
            id corresponding to a particular `actor`
        """
        ret = self._controlActorSelection(axis.value, actor_id, set=True)
        self._handle_err(ret, func="constrolActorSelection")

    @check_enums(axis=Axis)
    def _get_actor(self, axis):
        """
        Returns the 'actor' property (as an integer) of the specified axis
        """
        actor = self._controlActorSelection(axis.value, set=False)
        return actor

    @check_enums(axis=Axis)
    def _setContinuous(self, axis, forward, control):
        """ Allows for control of continuous movement for the specified actor

        forward = True -> movement in the positive direction for
        linear stages, and in the negative direction for goniometers

        forward = False -> movement in the negative direction for
        linear stages, and in the positive direction for goniometers

        control = True -> start motion in the specified direction

        control = False -> stop all continuous motion on the specified axis
        """
        if type(forward)!=bool:
            raise TypeError('forward must be a boolean')
        if forward:
            self.controlContinuousFwd(axis, control, set=True)
        if not forward:
            self.controlContinuousBkwd(axis, control, set=True)

    def set_default_actors(self, actors):
        """ Sets the default list of actors used in various functions.

        Actors should be a list of instances of Actor
        """
        for actor in actors:
            if not isinstance(Actor):
                raise TypeError("actors must be a list of instances of Actor")
        self._default_actors = actors

    def wait_until_at_position(self, actors=None, delta_pos=None):
        """Waits to return until all actors are at the target
        position

        If actors is None, then the default actors are used.  The default actors
        are set using set_default_actors
        """
        if actors is None:
            actors = self._default_actors
        if delta_pos is None:
            delta_pos = [None for i in range(len(actors))]
        for actor, delta in zip(actors, delta_pos):
            actor.wait_until_at_position(delta_pos=delta)

    def move_to(self, positions, actors=None, wait=False):
        """ Moves to the positions in the list positions.

        actors is a list of type Actor, or one can use the default actors, set
        by set_default_actors
        """
        if actors is None:
            actors = self._default_actors
        if len(actors) != len(positions):
            raise ValueError("positions must have the same length as actors")
        for actor, position in zip(actors, positions):
            actor.move_to(position)
        if wait:
            self.wait_until_at_position(actors)

    def get_target(self, actors=None):
        """ Gets the target positions of the actors in the list actors.

        Returns a list of target positions.

        actors is a list of type Actor, or one can use the default actors, set
        by set_default_actors
        """
        targets = []
        if actors is None:
            actors = self._default_actors
        for actor in actors:
            targets.append(actor.get_target())
        return targets

    def set_target(self, target, actors=None):
        """ Sets the target positions of the actors in the list actors.

        target is a list of position that are unitful pint quantities

        actors is a list of type Actor, or one can use the default actors, set
        by set_default_actors
        """
        if actors is None:
            actors = self._default_actors
        for actor, pos in zip(actors, target):
            actor.set_target(pos)

    def get_position(self, actors=None):
        """ Gets the positions of the actors in the list actors.

        actors is a list of type Actor, or one can use the default actors, set
        by set_default_actors
        """
        targets = []
        if actors is None:
            actors = self._default_actors
        for actor in actors:
            targets.append(actor.get_position())
        return targets
