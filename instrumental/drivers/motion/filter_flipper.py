# -*- coding: utf-8 -*-
# Copyright 2016 Christopher Rogers
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
from .. import _ParamDict
from ... import Q_
from ...errors import InstrumentTypeError
from ..util import check_units, check_enums

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

def _instrument(params):
    """ Possible params include 'ff_serial'"""
    d = {}
    if 'ff_serial' in params:
        d['serial'] = params['ff_serial']
    if not d:
        raise InstrumentTypeError()

    return Filter_Flipper(**d)

def list_instruments():
    flippers = []
    NiceFF = NiceFilterFlipper
    NiceFF.BuildDeviceList()
    device_list = NiceFF.GetDeviceListByTypeExt(FILTER_FLIPPER_TYPE)
    for serial_number in device_list:
        if serial_number != 0:
            serial_number = serial_number[:-1]
            params = _ParamDict("<Thorlabs_Filter_Flipper '{}'>".format(serial_number))
            params.module = 'motion.filter_flipper'
            params['ff_serial'] = serial_number
            flippers.append(params)
    return flippers


class NiceFilterFlipper(NiceLib):
    """ This class provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.FilterFlipper.dll"""
    _ret_wrap = None
    _struct_maker = None
    _ffi = ffi
    _lib = lib
    _prefix = ('FF_', 'TLI_')
    _buflen = 512

    BuildDeviceList = ()
    GetDeviceListSize = ()
    GetDeviceList = ('out')
    GetDeviceListByType = ('out', 'in')
# This function seemed not to be properly implemented in the .dll
#    GetDeviceListByTypes = ('out', 'in', 'in')
    GetDeviceListExt = ('buf', 'len')
    GetDeviceListByTypeExt = ('buf', 'len', 'in')
    GetDeviceListByTypesExt = ('buf', 'len', 'in', 'in')
    
    Flipper = NiceObjectDef({
        'GetDeviceInfo' : ('in', 'out'),
        'Open' : ('in'),
        'Close' : ('in'),
        'Identify' : ('in'),
        'GetHardwareInfo' : ('in', 'buf', 'len', 'out', 'out', 'buf', 'len',
                              'out', 'out', 'out'),
        'GetFirmwareVersion' : ('in'),
        'GetSoftwareVersion' : ('in'),
        'LoadSettings' : ('in'),
        'PersistSettings' : ('in'),
        'GetNumberPositions' : ('in'),
        'Home' : ('in'),
        'MoveToPosition' : ('in', 'in'),
        'GetPosition' : ('in'),
        'GetIOSettings' : ('in', 'out'),
        'GetTransitTime' : ('in'),
        'SetTransitTime' : ('in', 'in'),
        'RequestStatus' : ('in'),
        'GetStatusBits' : ('in'),
        'StartPolling' : ('in', 'in'),
        'PollingDuration' : ('in'),
        'StopPolling' : ('in'),
        'RequestSettings' : ('in'),
        'ClearMessageQueue' : ('in'),
        'RegisterMessageCallback' : ('in', 'in'),
        'MessageQueueSize' : ('in'),
        'GetNextMessage' : ('in', 'in', 'in', 'in'),
        'WaitForMessage' : ('in', 'in', 'in', 'in'),
    })


class Position(Enum):
        """ Represents the position of the flipper. """
        one = 1
        two = 2
        moving = 0


class Filter_Flipper(Motion):
    """ Driver for controlling Thorlabs Filter Flippers
    
    Takes the serial number of the device as a string.
    
    The polling period, which is how often the device updates its status, is
    passed as a pint quantity with units of time and is optional argument,
    with a default of 200ms
    """
    @check_units(polling_period='ms')
    def __init__(self, serial, polling_period='200ms'):
        """Parameters
        ----------
        serial_number: str
        
        polling_period: pint quantity with units of time """
        self.Position = Position
        self._NiceFF = NiceFilterFlipper.Flipper(serial);
        self.serial = serial
        
        self._open()
        self._NiceFF.LoadSettings()
        self._start_polling(polling_period)
    
    def _open(self):
        return self._NiceFF.Open()

    def close(self):
        return self._NiceFF.Close()

    @check_units(polling_period='ms')
    def _start_polling(self, polling_period='200ms'):
        """Starts polling the device to update its status with the given period
        provided, rounded to the nearest millisecond 
        
        Parameters
        ----------
        polling_period: pint quantity with units of time """
        self.polling_period = polling_period.to('ms').magnitude
        return self._NiceFF.StartPolling(self.polling_period)

    def get_position(self):
        """ Returns an instance of the Position enumerator indicating the
        position of the flipper at the most recent polling event. """
        position =  self._NiceFF.GetPosition()
        return Position(position)

    def flip(self):
        """ Flips from one position to the other.  """
        position = self.get_position()
        if position == Position.one:
            return self.move_to(Position.two)
        elif position == Position.two:
            return self.move_to(Position.one)
        else:
            raise Exception("Could not flip because the current position is not valid")

    @check_enums(position=Position)
    def move_to(self, position):
        """ Commands the flipper to move to the indicated position and then returns
        immediately.
        
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
        """ Commands the flipper to move to the indicated position and returns
        only once the flipper has reached that position.

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
        """ Returns True if the given position is a valid position to move to,
        and returns false otherwise
        
        Parameters
        ----------
        position: instance of Position """
        ismoving = position == Position.moving
        isposition = isinstance(position, Position)
        if  ismoving or not isposition:
            return False
        else:
            return True

    def home(self):
        """ Performs the homing function """
        return self._NiceFF.Home()

    def get_transit_time(self):
        """ Returns the transit time, which is the time to transition from
        one filter position to the next."""
        transit_time = self._NiceFF.GetTransitTime()
        return Q_(transit_time, 'ms')

    @check_units(transit_time='ms')
    def set_transit_time(self, transit_time='500ms'):
        """ Sets the transit time, which is the time to transition from
        one filter position to the next.
        Parameters
        ----------
        transit_time: pint quantity with units of time """
        transit_time = transit_time.to('ms').magnitude
        return int(self._NiceFF.SetTransitTime(transit_time))
