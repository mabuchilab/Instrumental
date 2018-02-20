# -*- coding: utf-8 -*-
# Copyright 2016-2018 Christopher Rogers, Nate Bogdanowicz
"""
Driver for controlling Thorlabs TDC001 T-Cube DC Servo Motor Controllers using the Kinesis SDK.

One must place Thorlabs.MotionControl.DeviceManager.dll and Thorlabs.MotionControl.TCube.DCServo.dll
in the path.
"""
from enum import Enum
from time import sleep
from numpy import zeros
import os.path
from nicelib import NiceLib, Sig, NiceObject, RetHandler, ret_return
from cffi import FFI
from . import Motion
from .. import ParamSet
from ... import Q_, u
from ...errors import Error
from ..util import check_units, check_enums
from ...util import to_str

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
    device_list = to_str(NiceTDC001.GetDeviceListByTypeExt(TDC001_TYPE)).split(',')
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
    _INST_PARAMS_ = ['serial']

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


@RetHandler(num_retvals=0)
def ret_success(success):
    if not success:
        raise TDC001Error('The function did not execute successfully')


@RetHandler(num_retvals=0)
def ret_errcheck(retval):
    if not (retval == 0 or retval is None):
        raise TDC001Error(error_dict[retval])


class NiceTDC001(NiceLib):
    """Mid-level wrapper for Thorlabs.MotionControl.TCube.DCServo.dll"""
    _ffi_ = ffi
    _ffilib_ = lib
    _prefix_ = ('CC_', 'TLI_')
    _buflen_ = 512
    _ret_ = ret_errcheck

    BuildDeviceList = Sig()
    GetDeviceListSize = Sig(ret=ret_return)
    GetDeviceInfo = Sig('in', 'out', ret=ret_success)
    GetDeviceList = Sig('out')
    GetDeviceListByType = Sig('out', 'in')
    GetDeviceListByTypes = Sig('out', 'in', 'in')
    GetDeviceListExt = Sig('buf', 'len')
    GetDeviceListByTypeExt = Sig('buf', 'len', 'in')
    GetDeviceListByTypesExt = Sig('buf', 'len', 'in', 'in')

    class TDC001(NiceObject):
        Open = Sig('in')
        Close = Sig('in', ret=ret_return)
        Identify = Sig('in', ret=ret_return)
        GetLEDswitches = Sig('in', ret=ret_return)
        SetLEDswitches = Sig('in', 'in')
        GetHardwareInfo = Sig('in', 'buf', 'len', 'out', 'out', 'buf', 'len', 'out', 'out', 'out')
        GetHardwareInfoBlock = Sig('in', 'out')
        GetHubBay = Sig('in', ret=ret_return)
        GetSoftwareVersion = Sig('in', ret=ret_return)
        LoadSettings = Sig('in', ret=ret_success)
        PersistSettings = Sig('in', ret=ret_success)
        DisableChannel = Sig('in')
        EnableChannel = Sig('in')
        GetNumberPositions = Sig('in', ret=ret_return)
        CanHome = Sig('in', ret=ret_success)
        NeedsHoming = Sig('in', ret=ret_return)
        Home = Sig('in')
        MoveToPosition = Sig('in', 'in')
        GetPosition = Sig('in', ret=ret_return)
        GetHomingVelocity = Sig('in', ret=ret_return)
        SetHomingVelocity = Sig('in', 'in')
        MoveRelative = Sig('in', 'in')
        GetJogMode = Sig('in', 'out', 'out')
        SetJogMode = Sig('in', 'in', 'in')
        SetJogStepSize = Sig('in', 'in')
        GetJogStepSize = Sig('in', ret=ret_return)
        GetJogVelParams = Sig('in', 'out', 'out')
        SetJogVelParams = Sig('in', 'in', 'in')
        MoveJog = Sig('in', 'in')
        SetVelParams = Sig('in', 'in', 'in')
        GetVelParams = Sig('in', 'out', 'out')
        MoveAtVelocity = Sig('in', 'in')
        SetDirection = Sig('in', 'in', ret=ret_return)
        StopImmediate = Sig('in')
        StopProfiled = Sig('in')
        GetBacklash = Sig('in', ret=ret_return)
        SetBacklash = Sig('in', 'in')
        GetPositionCounter = Sig('in', ret=ret_return)
        SetPositionCounter = Sig('in', 'in')
        GetEncoderCounter = Sig('in', ret=ret_return)
        SetEncoderCounter = Sig('in', 'in')
        GetLimitSwitchParams = Sig('in', 'out', 'out', 'out', 'out', 'out')
        SetLimitSwitchParams = Sig('in', 'in', 'in', 'in', 'in', 'in')
        GetSoftLimitMode = Sig('in', ret=ret_return)
        SetLimitsSoftwareApproachPolicy = Sig('in', 'in', ret=ret_return)
        GetButtonParams = Sig('in', 'out', 'out', 'out', 'out')
        SetButtonParams = Sig('in', 'in', 'in', 'in')
        SetPotentiometerParams = Sig('in', 'in', 'in', 'in')
        GetPotentiometerParams = Sig('in', 'in', 'out', 'out')
        GetVelParamsBlock = Sig('in', 'out')
        SetVelParamsBlock = Sig('in', 'in')
        SetMoveAbsolutePosition = Sig('in', 'in')
        GetMoveAbsolutePosition = Sig('in', ret=ret_return)
        MoveAbsolute = Sig('in')
        SetMoveRelativeDistance = Sig('in', 'in')
        GetMoveRelativeDistance = Sig('in', ret=ret_return)
        MoveRelativeDistance = Sig('in')
        GetHomingParamsBlock = Sig('in', 'out')
        SetHomingParamsBlock = Sig('in', 'in')
        GetJogParamsBlock = Sig('in', 'out')
        SetJogParamsBlock = Sig('in', 'in')
        GetButtonParamsBlock = Sig('in', 'out')
        SetButtonParamsBlock = Sig('in', 'in')
        GetPotentiometerParamsBlock = Sig('in', 'out')
        SetPotentiometerParamsBlock = Sig('in', 'in')
        GetLimitSwitchParamsBlock = Sig('in', 'out')
        SetLimitSwitchParamsBlock = Sig('in', 'in')
        GetDCPIDParams = Sig('in', 'out')
        SetDCPIDParams = Sig('in', 'in')
        SuspendMoveMessages = Sig('in')
        ResumeMoveMessages = Sig('in')
        RequestPosition = Sig('in')
        RequestStatusBits = Sig('in', ret=ret_return)
        GetStatusBits = Sig('in', ret=ret_return)
        StartPolling = Sig('in', 'in', ret=ret_success)
        PollingDuration = Sig('in', ret=ret_return)
        StopPolling = Sig('in', ret=ret_return)
        RequestSettings = Sig('in')
        GetStageAxisMinPos = Sig('in', ret=ret_return)
        GetStageAxisMaxPos = Sig('in', ret=ret_return)
        SetStageAxisLimits = Sig('in', 'in', 'in')
        SetMotorTravelMode = Sig('in', 'in')
        GetMotorTravelMode = Sig('in', ret=ret_return)
        SetMotorParams = Sig('in', 'in', 'in', 'in')
        GetMotorParams = Sig('in', 'out', 'out', 'out')
        SetMotorParamsExt = Sig('in', 'in', 'in', 'in')
        GetMotorParamsExt = Sig('in', 'out', 'out', 'out')
        ClearMessageQueue = Sig('in', ret=ret_return)
        RegisterMessageCallback = Sig('in', 'in', ret=ret_return)
        MessageQueueSize = Sig('in', ret=ret_return)
        GetNextMessage = Sig('in', 'out', 'out', 'out', ret=ret_success)
        WaitForMessage = Sig('in', 'in', 'in', 'in', ret=ret_success)


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
