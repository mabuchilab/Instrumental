# -*- coding: utf-8 -*-
"""
This script contains classes for controlling Thorlabs TDC001 T-Cube DC Servo
Motor Controllers.

One must place Thorlabs.MotionControl.DeviceManager.dll and Thorlabs.MotionControl.FilterFlipper.dll
in the path.

Copyright 2016 Christopher Rogers
"""

from enum import Enum
from time import sleep
from numpy import zeros
import os.path
from nicelib import NiceLib, NiceObject
from cffi import FFI
from . import Motion
from .. import _ParamDict
from ... import Q_, u
from ...errors import InstrumentTypeError
from ..util import check_units, check_enums

lib_name = 'Thorlabs.MotionControl.TCube.DCServo.dll'

TDC001_TYPE = 83

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

with open(os.path.join(os.path.dirname(__file__), '_tdc_001', 'tdc_001.h')) as f:
    ffi.cdef(f.read())
lib = ffi.dlopen(lib_name)

def _instrument(params):
    """ Possible params include 'tdc_serial'"""
    d = {}
    if 'tdc_serial' in params:
        d['serial'] = params['tdc_serial']
    if not d:
        raise InstrumentTypeError()
    
    return TDC001(**d)

def list_instruments():
    tdcs = []
    NiceTDC = NiceTDC001
    NiceTDC.BuildDeviceList()
    device_list = NiceTDC.GetDeviceListByTypeExt(TDC001_TYPE)
    for serial_number in device_list:
        if serial_number != 0:
            serial_number = serial_number[:-1]
            params = _ParamDict("<Thorlabs_DC_Servo_T-Cube '{}'>".format(serial_number))
            params.module = 'motion.tdc_001'
            params['tdc_serial'] = serial_number
            tdcs.append(params)
    return tdcs


class TravelMode(Enum):
    Linear = 1
    Rotational = 2


class SoftwareApproachPolicy(Enum):
    DisableOutsideRange = 0
    DisableFarOutsideRange = 1
    TruncateBeyondLimit = 2
    AllowAll = 3


class TDC001(Motion):
    """ Class for controlling Thorlabs TDC001 T-Cube DC Servo Motor Controllers
    
    Takes the serial number of the device as a string.
    
    The polling period, which is how often the device updates its status, is
    passed as a pint pint quantity with units of time and is optional argument,
    with a default of 200ms
    """

    def __init__(self, serial, polling_period=Q_('200ms'),
                 allow_all_moves=True):
        """Parameters
        ----------
        serial_number: str
        
        polling_period: pint quantity with units of time """
        self.SoftwareApproachPolicy = SoftwareApproachPolicy
        self.TravelMode = TravelMode
        self._NiceTDC = NiceTDC001.TDC001(serial)
        self.serial_number = serial
        
        self._open()
        self._start_polling(polling_period)
        self._NiceTDC.LoadSettings()
        self._set_real_world_units()
        
        if allow_all_moves:
            self._set_software_approach_policy(self.SoftwareApproachPolicy.AllowAll)
            stage_max_pos = 2**30
            self._NiceTDC.SetStageAxisLimits(-stage_max_pos, stage_max_pos)
            assert self._NiceTDC.GetStageAxisMaxPos() == stage_max_pos
            assert self._NiceTDC.GetStageAxisMinPos() == -stage_max_pos

    def _set_real_world_unit_conversion(self):
        steps_per_rev, gearbox_ratio, pitch = self.get_motor_params()
        cf = Q_(pitch/steps_per_rev/float(gearbox_ratio), self.real_world_units)
        self.encoder_to_real_world_units_conversion_factor = cf
  
    def _open(self):
        return self._NiceTDC.Open()

    def close(self):
        return self._NiceTDC.Close()

    @check_units(polling_period = 'ms')
    def _start_polling(self, polling_period='200ms'):
        """Starts polling the device to update its status with the given period
        provided, rounded to the nearest millisecond 
        
        Parameters
        ----------
        polling_period: pint quantity with units of time """
        self.polling_period = polling_period.to('ms').magnitude
        return self._NiceTDC.StartPolling(self.polling_period)

    def _set_real_world_units(self):
        travel_mode = self.TravelMode(self._NiceTDC.GetMotorTravelMode())
        if travel_mode == self.TravelMode.Linear:
            real_world_units = u('mm')
        if travel_mode == self.TravelMode.Rotational:
            real_world_units = u('degrees')
        self.real_world_units = real_world_units
        
        self._set_real_world_unit_conversion()
        return

    def get_status(self):
        self._NiceTDC.RequestStatusBits()
        status_bits = self._NiceTDC.GetStatusBits()
        return self.Status(status_bits)

    def set_motor_params(self, steps_per_rev, gearbox_ratio, pitch):
        """ Sets the motor stage parameters.
        
        Parameters
        ----------
        steps_per_rev: int
        gearbox_ratio: int
        pitch: float """
        self.pitch = pitch
        self.gearbox_ratio = gearbox_ratio
        self.steps_per_rev = steps_per_rev

        value = self._NiceTDC.SetMotorParams(steps_per_rev, gearbox_ratio, pitch)
        return value

    def get_motor_params(self):
        """ Gets the stage motor parameters.
        
        Returns
        -------
        (steps_per_rev: int,
        gearbox_ratio: int,
        pitch: float)"""
        steps_per_rev, gearbox_ratio, pitch, _ = self._NiceTDC.GetMotorParams()
        return int(steps_per_rev), int(gearbox_ratio), float(pitch)

    def get_position(self):
        """ Returns an instance of the Position enumerator indicating the
        position of the flipper at the most recent polling event. """
        self._NiceTDC.RequestPosition()
        position =  self._NiceTDC.GetPosition()
        return position*self.encoder_to_real_world_units_conversion_factor

    def move_to(self, position):
        """ Commands the motor to move to the indicated position and then returns
        immediately.
        
        Parameters
        ----------
        position: pint quantity of units self.real_world_units """
        position = self._get_encoder_value(position)
        value = self._NiceTDC.MoveToPosition(position)
        return value

    def _get_encoder_value(self, position):
        position.to(self.real_world_units)
        position = position/self.encoder_to_real_world_units_conversion_factor
        return int(position.magnitude)

    @check_units(delay='ms')
    def move_and_wait(self, position, delay='100ms', tol=1):
        """ Commands the flipper to move to the indicated position and returns
        only once the flipper has reached that position.

        Parameters
        ----------
        position: pint quantity of units self.real_world_units 
        delay: pint quantity with units of time
            the period with which the position of the motor is checked.
        tol: int
            the tolerance, in encoder units, to which the motor is considered
            at position"""
        self.move_to(position)
        while not self.at_position(position, tol):
            sleep(delay.to('s').magnitude)

    def at_position(self, position, tol=1):
        """Returns true if the motor is at the specified position.

        Parameters
        ----------
        position: pint quantity of units self.real_world_units """
        self._NiceTDC.RequestPosition()
        enc_position = self._get_encoder_value(position)
        at_pos = abs(self._NiceTDC.GetPosition() - enc_position) <= tol
        return at_pos

    def home(self):
        """ Performs the homing function """
        return self._NiceTDC.Home()

    @check_enums(software_approach_policy=SoftwareApproachPolicy)
    def _set_software_approach_policy(self, software_approach_policy):
        """ Sets the the 'software approach policy', which controls over what
        range of values the motor is allowed to move to.   This is done using
        the SoftwareApproachPolicy enumerator """
        self._NiceTDC.SetLimitsSoftwareApproachPolicy(software_approach_policy.value)

    def _get_software_approach_policy(self):
        """ Gets the the 'software approach policy', which controls over what
        range of values the motor is allowed to move to.   This is done using
        the SoftwareApproachPolicy enumerator """
        software_approach_policy = self._NiceTDC.GetSoftLimitMode()
        return self.SoftwareApproachPolicy(software_approach_policy)

    class Status():
        def __init__(self, status_bits):
            nbits=32
            self._status_bits = status_bits
            self._bits = zeros(nbits)
            for i in range(nbits):
                self._bits[i] = (status_bits%2**(i+1))/2**i
            self.CW_LimSwitch_Contact = bool(self._bits[0])
            self.CCW_LimSwitch_Contact = bool(self._bits[1])
            self.MotorMovingCW = bool(self._bits[4])
            self.MotorMovingCCW = bool(self._bits[5])
            self.MotorJoggingCW = bool(self._bits[6])
            self.MotorJoggingCCW = bool(self._bits[7])
            self.MotorHoming = bool(self._bits[9])
            self.MotorHomed = bool(self._bits[10])
            self.isActive = bool(self._bits[29])
            self.isEnabled = bool(self._bits[31])
            
            temp = self.MotorHoming or self.MotorJoggingCCW or self.MotorJoggingCW
            self.isMoving = temp or self.MotorMovingCCW or self.MotorMovingCW


class NiceTDC001(NiceLib):
    """ This class provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.TCube.DCServo.dll"""
    _err_wrap = None
    _struct_maker = None
    _ffi = ffi
    _lib = lib
    _prefix = ('CC_', 'TLI_')
    _buflen = 512

    BuildDeviceList = ()
    TLI_GetDeviceListSize = ()
    GetDeviceList = ('out')
    GetDeviceListByType = ('out', 'in')
    GetDeviceListByTypes = ('out', 'in', 'in')
    GetDeviceListExt = ('buf', 'len')
    GetDeviceListByTypeExt = ('buf', 'len', 'in')
    GetDeviceListByTypesExt = ('buf', 'len', 'in', 'in')

    TDC001 = NiceObject({
        'GetDeviceInfo': ('in', 'out'),
        'Open': ('in'),
        'Close': ('in'),
        'Identify': ('in'),
        'GetLEDswitches': ('in'),
        'SetLEDswitches': ('in', 'in'),
        'GetHardwareInfo': ('in', 'buf', 'len', 'out', 'out', 'buf', 'len',
                              'out', 'out', 'out'),
        'GetHardwareInfoBlock': ('in', 'out'),
        'GetHubBay': ('in'),
        'GetSoftwareVersion': ('in'),
        'LoadSettings': ('in'),
        'PersistSettings': ('in'),
        'DisableChannel': ('in'),
        'EnableChannel': ('in'),
        'GetNumberPositions': ('in'),
        'CanHome': ('in'),
        'NeedsHoming': ('in'),
        'Home': ('in'),
        'MoveToPosition': ('in', 'in'),
        'GetPosition': ('in'),
        'GetHomingVelocity': ('in'),
        'SetHomingVelocity': ('in', 'in'),
        'MoveRelative': ('in', 'in'),
        'GetJogMode': ('in', 'out', 'out'),
        'SetJogMode': ('in', 'in', 'in'),
        'SetJogStepSize': ('in', 'in'),
        'GetJogStepSize': ('in'),
        'GetJogVelParams': ('in', 'out', 'out'),
        'SetJogVelParams': ('in', 'in', 'in'),
        'MoveJog': ('in', 'in'),
        'SetVelParams': ('in', 'in', 'in'),
        'GetVelParams': ('in', 'out', 'out'),
        'MoveAtVelocity': ('in', 'in'),
        'SetDirection': ('in', 'in'),
        'StopImmediate': ('in'),
        'StopProfiled': ('in'),
        'GetBacklash': ('in'),
        'SetBacklash': ('in', 'in'),
        'GetPositionCounter': ('in'),
        'SetPositionCounter': ('in', 'in'),
        'GetEncoderCounter': ('in'),
        'SetEncoderCounter': ('in', 'in'),
        'GetLimitSwitchParams': ('in', 'out', 'out', 'out', 'out', 'out'),
        'SetLimitSwitchParams': ('in', 'in', 'in', 'in', 'in', 'in'),
        'GetSoftLimitMode': ('in'),
        'SetLimitsSoftwareApproachPolicy': ('in', 'in'),
        'GetButtonParams': ('in', 'out', 'out', 'out', 'out'),
        'SetButtonParams': ('in', 'in', 'in', 'in'),
        'SetPotentiometerParams': ('in', 'in', 'in', 'in'),
        'GetPotentiometerParams': ('in', 'in', 'out', 'out'),
        'GetVelParamsBlock': ('in', 'out'),
        'SetVelParamsBlock': ('in', 'in'),
        'SetMoveAbsolutePosition': ('in', 'in'),
        'GetMoveAbsolutePosition': ('in'),
        'MoveAbsolute': ('in'),
        'SetMoveRelativeDistance': ('in', 'in'),
        'GetMoveRelativeDistance': ('in'),
        'MoveRelativeDistance': ('in'),
        'GetHomingParamsBlock': ('in', 'out'),
        'SetHomingParamsBlock': ('in', 'in'),
        'GetJogParamsBlock': ('in', 'out'),
        'SetJogParamsBlock': ('in', 'in'),
        'GetButtonParamsBlock': ('in', 'out'),
        'SetButtonParamsBlock': ('in', 'in'),
        'GetPotentiometerParamsBlock': ('in', 'out'),
        'SetPotentiometerParamsBlock': ('in', 'in'),
        'GetLimitSwitchParamsBlock': ('in', 'out'),
        'SetLimitSwitchParamsBlock': ('in', 'in'),
        'GetDCPIDParams': ('in', 'out'),
        'SetDCPIDParams': ('in', 'in'),
        'SuspendMoveMessages': ('in'),
        'ResumeMoveMessages': ('in'),
        'RequestPosition': ('in'),
        'RequestStatusBits': ('in'),
        'GetStatusBits': ('in'),    
        'StartPolling': ('in', 'in'),
        'PollingDuration': ('in'),
        'StopPolling': ('in'),
        'RequestSettings': ('in'),
        'GetStageAxisMinPos': ('in'),
        'GetStageAxisMaxPos': ('in'),
        'SetStageAxisLimits': ('in', 'in', 'in'),
        'SetMotorTravelMode': ('in', 'in'),
        'GetMotorTravelMode': ('in'),
        'SetMotorParams': ('in', 'in', 'in', 'in'),
        'GetMotorParams': ('in', 'out', 'out', 'out'),
        'SetMotorParamsExt': ('in', 'in', 'in', 'in'),
        'GetMotorParamsExt': ('in', 'out', 'out', 'out'),
        'ClearMessageQueue': ('in'),
        'RegisterMessageCallback': ('in', 'in'),
        'MessageQueueSize': ('in'),
        'GetNextMessage': ('in', 'out', 'out', 'out'),
        'WaitForMessage': ('in', 'in', 'in', 'in'),
    })
