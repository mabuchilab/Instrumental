# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Nate Bogdanowicz
"""
Driver for controlling Thorlabs Flipper Filters using the Kinesis SDK.

One must place Thorlabs.MotionControl.DeviceManager.dll and Thorlabs.MotionControl.FilterFlipper.dll
in the path
"""
from enum import Enum
from time import sleep
import os.path
from cffi import FFI
from nicelib import NiceLib, NiceObjectDef
from . import Motion
from .. import ParamSet
from ... import Q_
from ...errors import Error
from ..util import check_units, check_enums

_INST_PARAMS = ['serial']
_INST_CLASSES = ['Filter_Flipper']

FILTER_FLIPPER_TYPE = 37

lib_name = 'Thorlabs.MotionControl.FilterFlipper.dll'

ffi = FFI()
ffi.cdef("""
    typedef struct tagSAFEARRAYBOUND {
      ULONG cElements;
      LONG  lLbound;
    } SAFEARRAYBOUND, *LPSAFEARRAYBOUND;

        typedef struct tagSAFEARRAY {
      USHORT         cDims;
      USHORT         fFeatures;
      ULONG          cbElements;
      ULONG          cLocks;
      PVOID          pvData;
      SAFEARRAYBOUND rgsabound[1];
    } SAFEARRAY, *LPSAFEARRAY;
""")


with open(os.path.join(os.path.dirname(__file__), '_filter_flipper', 'FilterFlipper.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen(lib_name)


def list_instruments():
    NiceFF = NiceFilterFlipper
    NiceFF.BuildDeviceList()
    device_list = NiceFF.GetDeviceListByTypeExt(FILTER_FLIPPER_TYPE).split(',')
    return [ParamSet(Filter_Flipper, serial=serial_str)
            for serial_str in device_list
            if serial_str and int(serial_str[:2]) == FILTER_FLIPPER_TYPE]


class NiceFilterFlipper(NiceLib):
    """ Provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.FilterFlipper.dll"""
    _ret = 'error_code'
    _struct_maker = None
    _ffi = ffi
    _ffilib = lib
    _prefix = ('FF_', 'TLI_')
    _buflen = 512

    def _ret_bool_error_code(success):
        if not success:
            raise FilterFlipperError('The function did not execute successfully')

    def _ret_error_code(retval):
        if not (retval == 0 or retval is None):
            raise FilterFlipperError(error_dict[retval])

    BuildDeviceList = ()
    GetDeviceListSize = ({'ret': 'return'},)
    GetDeviceList = ('out')
    GetDeviceListByType = ('out', 'in')
    GetDeviceInfo = ('in', 'out', {'ret': 'bool_error_code'})

    # GetDeviceListByTypes seemed not to be properly implemented in the .dll
    #    GetDeviceListByTypes = ('out', 'in', 'in')
    GetDeviceListExt = ('buf', 'len')
    GetDeviceListByTypeExt = ('buf', 'len', 'in')
    GetDeviceListByTypesExt = ('buf', 'len', 'in', 'in')

    Flipper = NiceObjectDef({
        'Open': ('in'),
        'Close': ('in'),
        'Identify': ('in'),
        'GetHardwareInfo': ('in', 'buf', 'len', 'out', 'out', 'buf', 'len',
                            'out', 'out', 'out'),
        'GetFirmwareVersion': ('in', {'ret': 'return'}),
        'GetSoftwareVersion': ('in', {'ret': 'return'}),
        'LoadSettings': ('in', {'ret': 'bool_error_code'}),
        'PersistSettings': ('in', {'ret': 'bool_error_code'}),
        'GetNumberPositions': ('in', {'ret': 'return'}),
        'Home': ('in'),
        'MoveToPosition': ('in', 'in'),
        'GetPosition': ('in', {'ret': 'return'}),
        'GetIOSettings': ('in', 'out'),
        'GetTransitTime': ('in', {'ret': 'return'}),
        'SetTransitTime': ('in', 'in'),
        'RequestStatus': ('in'),
        'GetStatusBits': ('in', {'ret': 'return'}),
        'StartPolling': ('in', 'in', {'ret': 'bool_error_code'}),
        'PollingDuration': ('in', {'ret': 'return'}),
        'StopPolling': ('in'),
        'RequestSettings': ('in'),
        'ClearMessageQueue': ('in'),
        'RegisterMessageCallback': ('in', 'in'),
        'MessageQueueSize': ('in', {'ret': 'return'}),
        'GetNextMessage': ('in', 'in', 'in', 'in', {'ret': 'bool_error_code'}),
        'WaitForMessage': ('in', 'in', 'in', 'in', {'ret': 'bool_error_code'}),
    })


class Position(Enum):
        """ The position of the flipper. """
        one = 1
        two = 2
        moving = 0


class Filter_Flipper(Motion):
    """ Driver for controlling Thorlabs Filter Flippers

    The polling period, which is how often the device updates its status, is
    passed as a pint quantity with units of time and is optional argument,
    with a default of 200ms
    """
    @check_units(polling_period='ms')
    def _initialize(self, polling_period='200ms'):
        """
        Parameters
        ----------
        polling_period : pint Quantity with units of time
        """
        self.Position = Position
        self.serial = self._paramset['serial']
        self._NiceFF = NiceFilterFlipper.Flipper(self.serial)

        self._open()
        self._NiceFF.LoadSettings()
        self._start_polling(polling_period)

    def _open(self):
        return self._NiceFF.Open()

    def close(self):
        return self._NiceFF.Close()

    @check_units(polling_period='ms')
    def _start_polling(self, polling_period='200ms'):
        """Starts polling to periodically update the device status.

        Parameters
        ----------
        polling_period: pint quantity with units of time """
        self.polling_period = polling_period.to('ms').magnitude
        return self._NiceFF.StartPolling(self.polling_period)

    def get_position(self):
        """ Get the position of the flipper.

        Returns an instance of Position.
        Note that this represents the position at the most recent polling
        event."""
        position = self._NiceFF.GetPosition()
        return Position(position)

    def flip(self):
        """ Flips the position of the filter.  """
        position = self.get_position()
        if position == Position.one:
            return self.move_to(Position.two)
        elif position == Position.two:
            return self.move_to(Position.one)
        else:
            raise Exception("Could not flip because the current position is not valid")

    @check_enums(position=Position)
    def move_to(self, position):
        """ Moves the flipper to the indicated position.

        Returns immediatley.

        Parameters
        ----------
        position: instance of Position
            should not be 'Position.moving' """
        if not self.isValidPosition(position):
            raise ValueError("Not a valid position")
        position = position.value
        return self._NiceFF.MoveToPosition(position)

    @check_units(delay='ms')
    @check_enums(position=Position)
    def move_and_wait(self, position, delay='100ms'):
        """ Moves to the indicated position and waits until that position is
        reached.

        Parameters
        ----------
        position: instance of Position
            should not be 'Position.moving'
        delay: pint quantity with units of time
            the period with which the position of the flipper is checked."""
        current_position = self.get_position()
        if not self.isValidPosition(position):
            raise ValueError("Not a valid position")
        if current_position != position:
            transit_time = self.get_transit_time()
            self.move_to(position)
            sleep(transit_time.to('s').magnitude)
            while self.get_position() != position:
                sleep(delay.to('s').magnitude)

    @check_enums(position=Position)
    def isValidPosition(self, position):
        """ Indicates if it is possible to move to the given position.

        Parameters
        ----------
        position: instance of Position """
        ismoving = position == Position.moving
        isposition = isinstance(position, Position)
        if ismoving or not isposition:
            return False
        else:
            return True

    def home(self):
        """ Homes the device """
        return self._NiceFF.Home()

    def get_transit_time(self):
        """ Returns the transit time.

        The transit time is the time to transition from
        one filter position to the next."""
        transit_time = self._NiceFF.GetTransitTime()
        return Q_(transit_time, 'ms')

    @check_units(transit_time='ms')
    def set_transit_time(self, transit_time='500ms'):
        """ Sets the transit time.
        The transit time is the time to transition from
        one filter position to the next.

        Parameters
        ----------
        transit_time: pint quantity with units of time """
        transit_time = transit_time.to('ms').magnitude
        return int(self._NiceFF.SetTransitTime(transit_time))


class FilterFlipperError(Error):
    pass


error_dict = {
    0: 'OK - Success  ',
    1: 'InvalidHandle - The FTDI functions have not been initialized.',
    2: 'DeviceNotFound - The Device could not be found.',
    3: 'DeviceNotOpened - The Device must be opened before it can be accessed ',
    4: 'IOError - An I/O Error has occured in the FTDI chip.',
    5: 'InsufficientResources - There are Insufficient resources to run this application.',
    6: 'InvalidParameter - An invalid parameter has been supplied to the device.',
    7: 'DeviceNotPresent - The Device is no longer present',
    8: 'IncorrectDevice - The device detected does not match that expected./term>',
    32: 'ALREADY_OPEN - Attempt to open a device that was already open.',
    33: 'NO_RESPONSE - The device has stopped responding.',
    34: 'NOT_IMPLEMENTED - This function has not been implemented.',
    35: 'FAULT_REPORTED - The device has reported a fault.',
    36: 'INVALID_OPERATION - The function could not be completed at this time.',
    40: 'DISCONNECTING - The function could not be completed because the device is disconnected.',
    41: 'FIRMWARE_BUG - The firmware has thrown an error.',
    42: 'INITIALIZATION_FAILURE - The device has failed to initialize',
    43: 'INVALID_CHANNEL - An Invalid channel address was supplied.',
    37: 'UNHOMED - The device cannot perform this function until it has been Homed.',
    38: ('INVALID_POSITION - The function cannot be performed as it would result in an illegal '
         'position.'),
    39: 'INVALID_VELOCITY_PARAMETER - An invalid velocity parameter was supplied',
    44: 'CANNOT_HOME_DEVICE - This device does not support Homing ',
    45: 'TL_JOG_CONTINOUS_MODE - An invalid jog mode was supplied for the jog function.'
}
