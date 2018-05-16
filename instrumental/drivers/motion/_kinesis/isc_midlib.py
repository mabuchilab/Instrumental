# -*- coding: utf-8 -*-
# Copyright 2017-2018 Nate Bogdanowicz

from nicelib import load_lib, NiceLib, Sig, NiceObject, ret_return
from .common_midlib import ret_errcheck, ret_success, all_sigs


class NiceISC(NiceLib):
    """Mid-level wrapper for Thorlabs.MotionControl.IntegratedStepperMotors.dll"""
    _info_ = load_lib('isc_', __package__, builder='._build_kinesis',
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

        _sigs_ = {name: all_sigs[name] for name in [
            'Open',
            'Close',
            'Identify',
            'GetHardwareInfo',
            'GetFirmwareVersion',
            'GetSoftwareVersion',
            'LoadSettings',
            'PersistSettings',
            'GetNumberPositions',
            'CanHome',
            'Home',
            'NeedsHoming',
            'MoveToPosition',
            'GetPosition',
            'GetPositionCounter',
            'RequestStatus',
            'RequestStatusBits',
            'GetStatusBits',
            'StartPolling',
            'PollingDuration',
            'StopPolling',
            'RequestSettings',
            'ClearMessageQueue',
            'RegisterMessageCallback',
            'MessageQueueSize',
            'GetNextMessage',
            'WaitForMessage',
            'GetMotorParamsExt',
            'SetJogStepSize',
            'GetJogVelParams',
            'GetBacklash',
            'SetBacklash',
            'GetLimitSwitchParams',
            'GetLimitSwitchParamsBlock',
        ]}
