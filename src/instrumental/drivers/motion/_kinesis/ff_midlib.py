# -*- coding: utf-8 -*-
# Copyright 2017-2018 Christopher Rogers, Nate Bogdanowicz

from nicelib import load_lib, NiceLib, Sig, NiceObject, ret_return
from .tli_midlib import ret_errcheck, ret_success


class NiceFF(NiceLib):
    """Mid-level wrapper for Thorlabs.MotionControl.FilterFlipper.dll"""
    _info_ = load_lib('ff_', __package__, builder='._build_kinesis',
                      kwargs={'shortname': 'ff',
                              'sublib': 'Thorlabs.MotionControl.FilterFlipper'})
    _prefix_ = 'TLI_'
    _ret_ = ret_errcheck

    BuildDeviceList = Sig()
    GetDeviceListSize = Sig(ret=ret_return)
    GetDeviceListExt = Sig('buf', 'len')
    GetDeviceListByTypeExt = Sig('buf', 'len', 'in')
    GetDeviceListByTypesExt = Sig('buf', 'len', 'in', 'in')
    GetDeviceInfo = Sig('in', 'out', ret=ret_success)

    # GetDeviceList = Sig('out')
    # GetDeviceListByType = Sig('out', 'in', first_arg=False)
    # GetDeviceListByTypes = Sig('out', 'in', 'in', first_arg=False)

    class Flipper(NiceObject):
        _prefix_ = 'FF_'

        Open = Sig('in')
        Close = Sig('in')
        Identify = Sig('in')
        GetHardwareInfo = Sig('in', 'buf', 'len', 'out', 'out', 'buf', 'len', 'out', 'out', 'out')
        GetFirmwareVersion = Sig('in', ret=ret_return)
        GetSoftwareVersion = Sig('in', ret=ret_return)
        LoadSettings = Sig('in', ret=ret_success)
        PersistSettings = Sig('in', ret=ret_success)
        GetNumberPositions = Sig('in', ret=ret_return)
        Home = Sig('in')
        MoveToPosition = Sig('in', 'in')
        GetPosition = Sig('in', ret=ret_return)
        GetIOSettings = Sig('in', 'out')
        GetTransitTime = Sig('in', ret=ret_return)
        SetTransitTime = Sig('in', 'in')
        RequestStatus = Sig('in')
        GetStatusBits = Sig('in', ret=ret_return)
        StartPolling = Sig('in', 'in', ret=ret_success)
        PollingDuration = Sig('in', ret=ret_return)
        StopPolling = Sig('in')
        RequestSettings = Sig('in')
        ClearMessageQueue = Sig('in')
        RegisterMessageCallback = Sig('in', 'in')
        MessageQueueSize = Sig('in', ret=ret_return)
        GetNextMessage = Sig('in', 'in', 'in', 'in', ret=ret_success)
        WaitForMessage = Sig('in', 'in', 'in', 'in', ret=ret_success)
