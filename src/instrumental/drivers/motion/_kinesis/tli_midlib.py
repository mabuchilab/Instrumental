# -*- coding: utf-8 -*-
# Copyright 2018-2020 Nate Bogdanowicz

from nicelib import load_lib, NiceLib, Sig, RetHandler, ret_return, ret_ignore
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
    """Mid-level wrapper for Thorlabs Kinesis TLI_ functions"""
    # NOTE: Wraps FilterFlipper DLL now because as of August 2020, DeviceManager DLL does not
    # include simulation-related functions
    _info_ = load_lib('tli_', __package__, builder='._build_kinesis',
                      kwargs={'shortname': 'tli',
                              'sublib': 'Thorlabs.MotionControl.FilterFlipper'})
    _prefix_ = 'TLI_'
    _ret_ = ret_errcheck

    BuildDeviceList = Sig()
    GetDeviceListSize = Sig(ret=ret_return)
    GetDeviceListExt = Sig('buf', 'len')
    GetDeviceListByTypeExt = Sig('buf', 'len', 'in')
    GetDeviceListByTypesExt = Sig('buf', 'len', 'in', 'in')
    GetDeviceInfo = Sig('in', 'out', ret=ret_success)
    InitializeSimulations = Sig(ret=ret_ignore)
    UninitializeSimulations = Sig(ret=ret_ignore)
