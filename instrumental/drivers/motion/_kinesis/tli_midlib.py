# -*- coding: utf-8 -*-
# Copyright 2018 Nate Bogdanowicz

from nicelib import load_lib, NiceLib, Sig, RetHandler, ret_return
from .common import KinesisError


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret is not None and ret != 0:
        raise KinesisError(ret)


@RetHandler(num_retvals=0)
def ret_success(ret, funcname):
    if not ret:
        raise KinesisError(msg="Call to function '{}' failed".format(funcname))


class NiceTLI(NiceLib):
    """Mid-level wrapper for Thorlabs.MotionControl.DeviceManager.dll"""
    _info_ = load_lib('tli_', __package__, builder='._build_kinesis',
                      kwargs={'shortname': 'tli',
                              'sublib': 'Thorlabs.MotionControl.DeviceManager'})
    _prefix_ = 'TLI_'
    _ret_ = ret_errcheck

    BuildDeviceList = Sig()
    GetDeviceListSize = Sig(ret=ret_return)
    GetDeviceListExt = Sig('buf', 'len')
    GetDeviceListByTypeExt = Sig('buf', 'len', 'in')
    GetDeviceListByTypesExt = Sig('buf', 'len', 'in', 'in')
    GetDeviceInfo = Sig('in', 'out', ret=ret_success)
