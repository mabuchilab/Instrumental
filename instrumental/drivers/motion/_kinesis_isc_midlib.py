# -*- coding: utf-8 -*-
# Copyright 2017-2018 Nate Bogdanowicz

from nicelib import load_lib, NiceLib, Sig, NiceObject, RetHandler, ret_return
from ._kinesis_common import KinesisError


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret is not None and ret != 0:
        raise KinesisError(ret)


@RetHandler(num_retvals=0)
def ret_success(ret, funcname):
    if not ret:
        raise KinesisError(msg="Call to function '{}' failed".format(funcname))


class NiceISC(NiceLib):
    """Mid-level wrapper for Thorlabs.MotionControl.IntegratedStepperMotors.dll"""
    _info_ = load_lib('kinesis_isc_', __package__, builder='_build_kinesis',
                      kwargs={'shortname': 'isc',
                              'sublib': 'Thorlabs.MotionControl.IntegratedStepperMotors'})
    _prefix_ = 'TLI_'
    _ret_ = ret_errcheck

    BuildDeviceList = Sig()
    GetDeviceListSize = Sig(ret=ret_return)
    GetDeviceListExt = Sig('buf', 'len')
    GetDeviceListByTypeExt = Sig('buf', 'len', 'in')
    GetDeviceListByTypesExt = Sig('buf', 'len', 'in', 'in')
    GetDeviceInfo = Sig('in', 'out', ret=ret_success)

    # GetDeviceList = Sig('out')
    # GetDeviceListByType = Sig('out', 'in', dict(first_arg=False))
    # GetDeviceListByTypes = Sig('out', 'in', 'in', dict(first_arg=False))

    class Device(NiceObject):
        _prefix_ = 'ISC_'

        Open = Sig('in')
        Close = Sig('in')
        Identify = Sig('in')
        GetHardwareInfo = Sig('in', 'buf', 'len', 'out', 'out', 'buf', 'len', 'out', 'out', 'out')
        GetFirmwareVersion = Sig('in', ret=ret_return)
        GetSoftwareVersion = Sig('in', ret=ret_return)
        LoadSettings = Sig('in', ret=ret_success)
        PersistSettings = Sig('in', ret=ret_success)
        GetNumberPositions = Sig('in', ret=ret_return)
        CanHome = Sig('in', ret=ret_return)
        Home = Sig('in')
        NeedsHoming = Sig('in', ret=ret_return)
        MoveToPosition = Sig('in', 'in')
        GetPosition = Sig('in', ret=ret_return)
        GetPositionCounter = Sig('in', ret=ret_return)
        RequestStatus = Sig('in')
        RequestStatusBits = Sig('in')
        GetStatusBits = Sig('in', ret=ret_return)
        StartPolling = Sig('in', 'in', ret=ret_success)
        PollingDuration = Sig('in', ret=ret_return)
        StopPolling = Sig('in')
        RequestSettings = Sig('in')
        ClearMessageQueue = Sig('in')
        RegisterMessageCallback = Sig('in', 'in')
        MessageQueueSize = Sig('in', ret=ret_return)
        GetNextMessage = Sig('in', 'out', 'out', 'out', ret=ret_success)
        WaitForMessage = Sig('in', 'out', 'out', 'out', ret=ret_success)
        GetMotorParamsExt = Sig('in', 'out', 'out', 'out')
        SetJogStepSize = Sig('in', 'in')
        GetJogVelParams = Sig('in', 'out', 'out')
        GetBacklash = Sig('in', ret=ret_return)
        SetBacklash = Sig('in', 'in')
        GetLimitSwitchParams = Sig('in', 'out', 'out', 'out', 'out', 'out')
        GetLimitSwitchParamsBlock = Sig('in', 'out')
