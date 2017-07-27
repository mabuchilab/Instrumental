# -*- coding: utf-8 -*-
# Copyright 2016-2017 Christopher Rogers, Nate Bogdanowicz
"""
Driver for controlling Thorlabs TDC001 T-Cube DC Servo Motor Controllers using the Kinesis SDK.

One must place Thorlabs.MotionControl.DeviceManager.dll and Thorlabs.MotionControl.TCube.DCServo.dll
in the path.
"""
from enum import Enum
from time import sleep
from numpy import zeros
import os.path
from nicelib import NiceLib, NiceObjectDef
from cffi import FFI
from . import Motion
from .. import ParamSet
from ... import Q_, u
from ...errors import Error
from ..util import check_units, check_enums

_INST_PARAMS = ['serial']
_INST_CLASSES = ['TDC001']

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


def list_instruments():
    NiceTDC001.BuildDeviceList()
    device_list = NiceTDC001.GetDeviceListByTypeExt(TDC001_TYPE).split(',')
    return [ParamSet(TDC001, serial=serial_str)
            for serial_str in device_list
            if serial_str and int(serial_str[:2]) == TDC001_TYPE]


class TravelMode(Enum):
    Linear = 1
    Rotational = 2


class SoftwareApproachPolicy(Enum):
    DisableOutsideRange = 0
    DisableFarOutsideRange = 1
    TruncateBeyondLimit = 2
    AllowAll = 3


class TDC001(Motion):
    """ Controlling Thorlabs TDC001 T-Cube DC Servo Motor Controllers

    The polling period, which is how often the device updates its status, is
    passed as a pint pint quantity with units of time and is optional argument,
    with a default of 200ms
    """

    @check_units(polling_period='ms')
    def _initialize(self, polling_period='200ms', allow_all_moves=True):
        """
        Parameters
        ----------
        polling_period : pint Quantity with units of time
        """
        self.SoftwareApproachPolicy = SoftwareApproachPolicy
        self.TravelMode = TravelMode
        self.serial_number = self._paramset['serial']
        self._NiceTDC = NiceTDC001.TDC001(self.serial_number)

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
        """Starts polling to periodically update the device status.

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
        """ Returns the status registry bits from the device."""
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
        steps_per_rev, gearbox_ratio, pitch = self._NiceTDC.GetMotorParams()
        return int(steps_per_rev), int(gearbox_ratio), float(pitch)

    def get_position(self):
        """ Returns the position of the motor.

        Note that this represents the position at the most recent polling
        event."""
        self._NiceTDC.RequestPosition()
        position = self._NiceTDC.GetPosition()
        return position*self.encoder_to_real_world_units_conversion_factor

    def move_to(self, position):
        """ Moves to the indicated position


        Returns immediately.

        Parameters
        ----------
        position: pint quantity of units self.real_world_units """
        position = Q_(position)
        position = self._get_encoder_value(position)
        value = self._NiceTDC.MoveToPosition(position)
        return value

    def _get_encoder_value(self, position):
        position = position.to(self.real_world_units)
        position = position/self.encoder_to_real_world_units_conversion_factor
        return int(position.magnitude)

    @check_units(delay='ms')
    def move_and_wait(self, position, delay='100ms', tol=1):
        """ Moves to the indicated position and waits until that position is
        reached.

        Parameters
        ----------
        position: pint quantity of units self.real_world_units
        delay: pint quantity with units of time
            the period with which the position of the motor is checked.
        tol: int
            the tolerance, in encoder units, to which the motor is considered
            at position"""
        position = Q_(position)
        self.move_to(position)
        while not self.at_position(position, tol):
            sleep(delay.to('s').magnitude)

    def at_position(self, position, tol=1):
        """Indicates whether the motor is at the given position.



        Parameters
        ----------
        position: pint quantity of units self.real_world_units
        tol: int representing the number of encoder counts within which the
        motor is considered to be at position"""
        position = Q_(position)
        self._NiceTDC.RequestPosition()
        enc_position = self._get_encoder_value(position)
        at_pos = abs(self._NiceTDC.GetPosition() - enc_position) <= tol
        return at_pos

    def home(self):
        """ Homes the device """
        return self._NiceTDC.Home()

    @check_enums(software_approach_policy=SoftwareApproachPolicy)
    def _set_software_approach_policy(self, software_approach_policy):
        """ Controls what range of values the motor is allowed to move to.

        This is done using the SoftwareApproachPolicy enumerator """
        self._NiceTDC.SetLimitsSoftwareApproachPolicy(software_approach_policy.value)

    def _get_software_approach_policy(self):
        """ Gets the range of values the motor is allowed to move to.

        Returns an instance of SoftwareApproachPolicy enumerator """
        software_approach_policy = self._NiceTDC.GetSoftLimitMode()
        return self.SoftwareApproachPolicy(software_approach_policy)

    class Status():
        """ Stores information about the status of the device from the status
        bits. """
        def __init__(self, status_bits):
            nbits = 32
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
    """ Provides a convenient low-level wrapper for the library
    Thorlabs.MotionControl.TCube.DCServo.dll"""
    _ret = 'error_code'
    _struct_maker = None
    _ffi = ffi
    _ffilib = lib
    _prefix = ('CC_', 'TLI_')
    _buflen = 512

    def _ret_bool_error_code(success):
        if not success:
            raise TDC001Error('The function did not execute successfully')

    def _ret_error_code(retval):
        if not (retval == 0 or retval is None):
            raise TDC001Error(error_dict[retval])

    BuildDeviceList = ()
    GetDeviceListSize = ({'ret': 'return'},)
    GetDeviceInfo = ('in', 'out', {'ret': 'bool_error_code'})
    GetDeviceList = ('out')
    GetDeviceListByType = ('out', 'in')
    GetDeviceListByTypes = ('out', 'in', 'in')
    GetDeviceListExt = ('buf', 'len')
    GetDeviceListByTypeExt = ('buf', 'len', 'in')
    GetDeviceListByTypesExt = ('buf', 'len', 'in', 'in')

    TDC001 = NiceObjectDef({
        'Open': ('in'),
        'Close': ('in', {'ret': 'return'}),
        'Identify': ('in', {'ret': 'return'}),
        'GetLEDswitches': ('in', {'ret': 'return'}),
        'SetLEDswitches': ('in', 'in'),
        'GetHardwareInfo': ('in', 'buf', 'len', 'out', 'out', 'buf', 'len', 'out', 'out', 'out'),
        'GetHardwareInfoBlock': ('in', 'out'),
        'GetHubBay': ('in', {'ret': 'return'}),
        'GetSoftwareVersion': ('in', {'ret': 'return'}),
        'LoadSettings': ('in', {'ret': 'bool_error_code'}),
        'PersistSettings': ('in', {'ret': 'bool_error_code'}),
        'DisableChannel': ('in'),
        'EnableChannel': ('in'),
        'GetNumberPositions': ('in', {'ret': 'return'}),
        'CanHome': ('in', {'ret': 'bool_error_code'}),
        'NeedsHoming': ('in', {'ret': 'return'}),
        'Home': ('in'),
        'MoveToPosition': ('in', 'in'),
        'GetPosition': ('in', {'ret': 'return'}),
        'GetHomingVelocity': ('in', {'ret': 'return'}),
        'SetHomingVelocity': ('in', 'in'),
        'MoveRelative': ('in', 'in'),
        'GetJogMode': ('in', 'out', 'out'),
        'SetJogMode': ('in', 'in', 'in'),
        'SetJogStepSize': ('in', 'in'),
        'GetJogStepSize': ('in', {'ret': 'return'}),
        'GetJogVelParams': ('in', 'out', 'out'),
        'SetJogVelParams': ('in', 'in', 'in'),
        'MoveJog': ('in', 'in'),
        'SetVelParams': ('in', 'in', 'in'),
        'GetVelParams': ('in', 'out', 'out'),
        'MoveAtVelocity': ('in', 'in'),
        'SetDirection': ('in', 'in', {'ret': 'return'}),
        'StopImmediate': ('in'),
        'StopProfiled': ('in'),
        'GetBacklash': ('in', {'ret': 'return'}),
        'SetBacklash': ('in', 'in'),
        'GetPositionCounter': ('in', {'ret': 'return'}),
        'SetPositionCounter': ('in', 'in'),
        'GetEncoderCounter': ('in', {'ret': 'return'}),
        'SetEncoderCounter': ('in', 'in'),
        'GetLimitSwitchParams': ('in', 'out', 'out', 'out', 'out', 'out'),
        'SetLimitSwitchParams': ('in', 'in', 'in', 'in', 'in', 'in'),
        'GetSoftLimitMode': ('in', {'ret': 'return'}),
        'SetLimitsSoftwareApproachPolicy': ('in', 'in', {'ret': 'return'}),
        'GetButtonParams': ('in', 'out', 'out', 'out', 'out'),
        'SetButtonParams': ('in', 'in', 'in', 'in'),
        'SetPotentiometerParams': ('in', 'in', 'in', 'in'),
        'GetPotentiometerParams': ('in', 'in', 'out', 'out'),
        'GetVelParamsBlock': ('in', 'out'),
        'SetVelParamsBlock': ('in', 'in'),
        'SetMoveAbsolutePosition': ('in', 'in'),
        'GetMoveAbsolutePosition': ('in', {'ret': 'return'}),
        'MoveAbsolute': ('in'),
        'SetMoveRelativeDistance': ('in', 'in'),
        'GetMoveRelativeDistance': ('in', {'ret': 'return'}),
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
        'RequestStatusBits': ('in', {'ret': 'return'}),
        'GetStatusBits': ('in', {'ret': 'return'}),
        'StartPolling': ('in', 'in', {'ret': 'bool_error_code'}),
        'PollingDuration': ('in', {'ret': 'return'}),
        'StopPolling': ('in', {'ret': 'return'}),
        'RequestSettings': ('in'),
        'GetStageAxisMinPos': ('in', {'ret': 'return'}),
        'GetStageAxisMaxPos': ('in', {'ret': 'return'}),
        'SetStageAxisLimits': ('in', 'in', 'in'),
        'SetMotorTravelMode': ('in', 'in'),
        'GetMotorTravelMode': ('in', {'ret': 'return'}),
        'SetMotorParams': ('in', 'in', 'in', 'in'),
        'GetMotorParams': ('in', 'out', 'out', 'out'),
        'SetMotorParamsExt': ('in', 'in', 'in', 'in'),
        'GetMotorParamsExt': ('in', 'out', 'out', 'out'),
        'ClearMessageQueue': ('in', {'ret': 'return'}),
        'RegisterMessageCallback': ('in', 'in', {'ret': 'return'}),
        'MessageQueueSize': ('in', {'ret': 'return'}),
        'GetNextMessage': ('in', 'out', 'out', 'out', {'ret': 'bool_error_code'}),
        'WaitForMessage': ('in', 'in', 'in', 'in', {'ret': 'bool_error_code'}),
    })


class TDC001Error(Error):
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
