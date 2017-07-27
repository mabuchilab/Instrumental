# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Dodd Gray, and Nate Bogdanowicz
"""
Driver for controlling Thorlabs Kinesis devices. Currently only directs the K10CR1 rotation stage.
"""
from __future__ import division
import logging as log
from enum import Enum
from nicelib import NiceLib, NiceObjectDef, load_lib

from . import Motion
from .. import ParamSet
from ..util import check_units
from ... import u, Q_

_INST_PARAMS = ['serial']
_INST_CLASSES = ['K10CR1']

__all__ = ['K10CR1']


# Message Enums
#
class MessageType(Enum):
    GenericDevice = 0
    GenericPiezo = 1
    GenericMotor = 2
    GenericDCMotor = 3
    GenericSimpleMotor = 4
    RackDevice = 5
    Laser = 6
    TECCtlr = 7
    Quad = 8
    NanoTrak = 9
    Specialized = 10
    Solenoid = 11


class GenericDevice(Enum):
    SettingsInitialized = 0
    SettingsUpdated = 1
    Error = 2
    Close = 3


class GenericMotor(Enum):
    Homed = 0
    Moved = 1
    Stopped = 2
    LimitUpdated = 3


class GenericDCMotor(Enum):
    Error = 0
    Status = 1


MessageIDs = {
    MessageType.GenericDevice: GenericDevice,
    MessageType.GenericMotor: GenericMotor,
    MessageType.GenericDCMotor: GenericDCMotor
}


def list_instruments():
    NiceKinesisISC.BuildDeviceList()
    serial_nums = NiceKinesisISC.GetDeviceListExt().split(',')
    return [ParamSet(K10CR1, serial=serial)
            for serial in serial_nums
            if serial]


class KinesisError(Exception):
    messages = {
        0: 'Success',
        1: 'The FTDI functions have not been initialized',
        2: 'The device could not be found. Make sure to call TLI_BuildDeviceList().',
        3: 'The device must be opened before it can be accessed',
        4: 'An I/O Error has occured in the FTDI chip',
        5: 'There are insufficient resources to run this application',
        6: 'An invalid parameter has been supplied to the device',
        7: 'The device is no longer present',
        8: 'The device detected does not match that expected',
        32: 'The device is already open',
        33: 'The device has stopped responding',
        34: 'This function has not been implemented',
        35: 'The device has reported a fault',
        36: 'The function could not be completed because the device is disconnected',
        41: 'The firmware has thrown an error',
        42: 'The device has failed to initialize',
        43: 'An invalid channel address was supplied',
        37: 'The device cannot perform this function until it has been Homed',
        38: 'The function cannot be performed as it would result in an illegal position',
        39: 'An invalid velocity parameter was supplied. The velocity must be greater than zero',
        44: 'This device does not support Homing. Check the Limit switch parameters are correct',
        45: 'An invalid jog mode was supplied for the jog function',
    }

    def __init__(self, code=None, msg=''):
        if code is not None and not msg:
            msg = '(0x{:X}) {}'.format(code, self.messages[code])
        super(KinesisError, self).__init__(msg)
        self.code = code


class NiceKinesisISC(NiceLib):
    """ This class provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.FilterFlipper.dll"""
    _info = load_lib('kinesis', __package__)

    #
    # Error wrapping functions
    #
    def _ret(ret):
        if ret != 0:
            raise KinesisError(ret)

    def _ret_success(ret, funcname):
        if not ret:
            raise KinesisError(msg="Call to function '{}' failed".format(funcname))

    #
    # Function signatures
    #
    _prefix = 'TLI_'

    BuildDeviceList = ()
    GetDeviceListSize = ({'ret': 'return'},)
    GetDeviceListExt = ('buf', 'len')
    GetDeviceListByTypeExt = ('buf', 'len', 'in')
    GetDeviceListByTypesExt = ('buf', 'len', 'in', 'in')
    GetDeviceInfo = ('in', 'out')

    # GetDeviceList = ('out')
    # GetDeviceListByType = ('out', 'in', dict(first_arg=False))
    # GetDeviceListByTypes = ('out', 'in', 'in', dict(first_arg=False))

    Device = NiceObjectDef(prefix='ISC_', attrs=dict(
        Open = ('in'),
        Close = ('in', {'ret': 'return'}),
        Identify = ('in', {'ret': 'ignore'}),
        GetHardwareInfo = ('in', 'buf', 'len', 'out', 'out', 'buf', 'len', 'out', 'out', 'out'),
        GetFirmwareVersion = ('in', {'ret': 'return'}),
        GetSoftwareVersion = ('in', {'ret': 'return'}),
        LoadSettings = ('in', {'ret': 'success'}),
        PersistSettings = ('in', {'ret': 'success'}),
        GetNumberPositions = ('in', {'ret': 'return'}),
        Home = ('in'),
        NeedsHoming = ('in', {'ret': 'return'}),
        MoveToPosition = ('in', 'in'),
        GetPosition = ('in', {'ret': 'return'}),
        RequestStatus = ('in'),
        RequestStatusBits = ('in'),
        GetStatusBits = ('in', {'ret': 'return'}),
        StartPolling = ('in', 'in', {'ret': 'success'},),
        PollingDuration = ('in', {'ret': 'return'}),
        StopPolling = ('in', {'ret': 'ignore'}),
        RequestSettings = ('in'),
        ClearMessageQueue = ('in', {'ret': 'ignore'}),
        RegisterMessageCallback = ('in', 'in', {'ret': 'ignore'}),
        MessageQueueSize = ('in', {'ret': 'return'}),
        GetNextMessage = ('in', 'out', 'out', 'out', {'ret': 'success'}),
        WaitForMessage = ('in', 'out', 'out', 'out', {'ret': 'success'}),
        GetMotorParamsExt = ('in', 'out', 'out', 'out'),
        SetJogStepSize = ('in', 'in'),
        GetJogVelParams = ('in', 'out', 'out'),
        GetBacklash = ('in', {'ret': 'return'}),
        SetBacklash = ('in', 'in'),
    ))


STATUS_MOVING_CW = 0x10
STATUS_MOVING_CCW = 0x20
STATUS_JOGGING_CW = 0x40
STATUS_JOGGING_CCW = 0x80


class K10CR1(Motion):
    """ Class for controlling Thorlabs K10CR1 integrated stepper rotation stages

    Takes the serial number of the device as a string as well as the gear box ratio,
    steps per revolution and microsteps per step as integers. It also takes the polling
    period as a pint quantity.

    The polling period, which is how often the device updates its status, is
    passed as a pint pint quantity with units of time and is optional argument,
    with a default of 200ms
    """
    _lib = NiceKinesisISC

    # Enums
    MessageType = MessageType
    GenericDevice = GenericDevice
    GenericMotor = GenericMotor
    GenericDCMotor = GenericDCMotor

    @check_units(polling_period='ms')
    def _initialize(self, gear_box_ratio=120, steps_per_rev=200, micro_steps_per_step=2048,
                    polling_period='200ms'):
        offset = self._paramset.get('offset', '0 deg')

        self.serial = self._paramset['serial']
        self.offset = offset
        self._unit_scaling = (gear_box_ratio * micro_steps_per_step *
                              steps_per_rev / (360.0 * u.deg))
        self._open()
        self._start_polling(polling_period)
        self._wait_for_message(0, 0)  # Make sure status has been loaded before we return

    def _open(self):
        NiceKinesisISC.BuildDeviceList()  # Necessary?
        self.dev = NiceKinesisISC.Device(self.serial)
        self.dev.Open()

    def close(self):
        self.dev.StopPolling()
        self.dev.Close()

    @check_units(polling_period='ms')
    def _start_polling(self, polling_period='200ms'):
        """Starts polling the device to update its status with the given period provided, rounded
        to the nearest millisecond

        Parameters
        ----------
        polling_period: pint quantity with units of time
        """
        self.polling_period = polling_period
        self.dev.StartPolling(self.polling_period.m_as('ms'))

    @check_units(angle='deg')
    def move_to(self, angle, wait=False):
        """Rotate the stage to the given angle

        Parameters
        ----------
        angle : Quantity
            Angle that the stage will rotate to. Takes the stage offset into account.
        """
        log.debug("Moving stage to {}".format(angle))
        log.debug("Current position is {}".format(self.position))
        self.dev.ClearMessageQueue()
        self.dev.MoveToPosition(self._to_dev_units(angle + self.offset))
        if wait:
            self.wait_for_move()

    def _wait_for_message(self, match_type, match_id):
        msg_type, msg_id, msg_data = self.dev.WaitForMessage()
        log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))
        while msg_type != match_type or msg_id != match_id:
            msg_type, msg_id, msg_data = self.dev.WaitForMessage()
            log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))

    def _check_for_message(self, match_type, match_id):
        """Check if a message of the given type and id is in the queue"""
        while True:
            try:
                msg_type, msg_id, msg_data = self.dev.GetNextMessage()
            except KinesisError:
                return False

            log.debug("Received kinesis message ({},{},{})".format(msg_type, msg_id, msg_data))
            if msg_type == match_type and msg_id == match_id:
                return True

    def wait_for_move(self):
        """Wait for the most recent move to complete"""
        self._wait_for_message(2, 1)

    def move_finished(self):
        """Check if the most recent move has finished"""
        return self._check_for_message(2, 1)

    def _to_real_units(self, dev_units):
        return (dev_units / self._unit_scaling).to('deg')

    @check_units(real_units='deg')
    def _to_dev_units(self, real_units):
        return int(round(float(real_units * self._unit_scaling)))

    def home(self, wait=False):
        """Home the stage

        Parameters
        ----------
        wait : bool, optional
            Wait until the stage has finished homing to return
        """
        self.dev.ClearMessageQueue()
        self.dev.Home()

        if wait:
            self.wait_for_home()

    def wait_for_home(self):
        """Wait for the most recent homing operation to complete"""
        self._wait_for_message(2, 0)

    def homing_finished(self):
        """Check if the most recent homing operation has finished"""
        return self._check_for_message(2, 0)

    @property
    def needs_homing(self):
        """True if the device needs to be homed before a move can be performed"""
        return bool(self.dev.NeedsHoming())

    @property
    def offset(self):
        return self._offset

    @offset.setter
    @check_units(offset='deg')
    def offset(self, offset):
        self._offset = offset

    @property
    def position(self):
        return self._to_real_units(self.dev.GetPosition()) - self.offset

    @property
    def is_homing(self):
        return bool(self.dev.GetStatusBits() & 0x00000200)

    @property
    def is_moving(self):
        return bool(self.dev.GetStatusBits() & 0x00000030)

    def get_next_message(self):
        msg_type, msg_id, msg_data = self.dev.GetNextMessage()
        type = MessageType(msg_type)
        id = MessageIDs[type](msg_id)
        return (type, id, msg_data)

    def get_messages(self):
        messages = []
        while True:
            try:
                messages.append(self.get_next_message())
            except Exception:
                break
        return messages
