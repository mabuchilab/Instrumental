from __future__ import division

from .... import u
from ....log import get_logger
from ... import Facet
from ...util import check_units
from .. import Motion
from .isc_midlib import NiceISC
from .common import (KinesisError, MessageType, GenericDevice, GenericMotor,
                     GenericDCMotor, MessageIDs)
import nicelib  # noqa (nicelib dep is hidden behind import of isc_midlib)

log = get_logger(__name__)

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
    _INST_PARAMS_ = ['serial']

    _lib = NiceISC

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
        self._wait_for_message(GenericDevice.SettingsInitialized)

    def _open(self):
        NiceISC.BuildDeviceList()  # Necessary?
        self.dev = NiceISC.Device(self.serial)
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

    def _decode_message(self, msg_tup):
        msg_type_int, msg_id_int, msg_data_int = msg_tup
        msg_type = MessageType(msg_type_int)
        msg_id = MessageIDs[msg_type](msg_id_int)
        return (msg_id, msg_data_int)

    def _wait_for_message(self, match_id):
        if not isinstance(match_id, (GenericDevice, GenericMotor, GenericDCMotor)):
            raise ValueError("Must specify message ID via enum")

        msg_id, msg_data = self._decode_message(self.dev.WaitForMessage())
        log.debug("Received kinesis message ({}: {})".format(msg_id, msg_data))
        while msg_id is not match_id:
            msg_id, msg_data = self._decode_message(self.dev.WaitForMessage())
            log.debug("Received kinesis message ({}: {})".format(msg_id, msg_data))

    def _check_for_message(self, match_id):
        """Check if a message of the given type and id is in the queue"""
        if not isinstance(match_id, (GenericDevice, GenericMotor, GenericDCMotor)):
            raise ValueError("Must specify message ID via enum")

        while True:
            try:
                msg_id, msg_data = self._decode_message(self.dev.GetNextMessage())
            except KinesisError:
                return False

            log.debug("Received kinesis message ({}: {})".format(msg_id, msg_data))
            if msg_id is match_id:
                return True

    def wait_for_move(self):
        """Wait for the most recent move to complete"""
        self._wait_for_message(GenericMotor.Moved)

    def move_finished(self):
        """Check if the most recent move has finished"""
        return self._check_for_message(GenericMotor.Moved)

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
        self._wait_for_message(GenericMotor.Homed)

    def homing_finished(self):
        """Check if the most recent homing operation has finished"""
        return self._check_for_message(GenericMotor.Homed)

    @Facet
    def needs_homing(self):
        """True if the device needs to be homed before a move can be performed"""
        return bool(self.dev.NeedsHoming())

    @Facet(units='deg')
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset

    @Facet(units='deg')
    def position(self):
        return self._to_real_units(self.dev.GetPosition()) - self.offset

    @Facet
    def is_homing(self):
        return bool(self.dev.GetStatusBits() & 0x00000200)

    @Facet
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
