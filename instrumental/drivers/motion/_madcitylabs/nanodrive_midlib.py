# -*- coding: utf-8 -*-
"""
Created the 03/03/2022

@author: Sebastien Weber
"""

from nicelib import load_lib, NiceLib, Sig, RetHandler, ret_return, NiceObject
from instrumental.errors import Error, TimeoutError


class NanodriveError(Error):
    def __init__(self, code):
        for key in NiceNanodrive._defs:
            if NiceNanodrive._defs[key] == code:
                super().__init__(NiceNanodrive._defs[code])
                break


def get_device_index(index):
    return index


def get_device_channel_index(dev_index, channel_index):
    return dev_index, channel_index


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret <= 0:
        raise(NanodriveError(int(ret)))


class NiceNanodrive(NiceLib):
    _info_ = load_lib('nanodrive', __package__)
    _ret_ = ret_errcheck
    _prefix_ = 'MCL_'
    _buflen_ = 128

    DLLVersion = Sig('inout', 'inout')

    InitHandle = Sig()
    GrabHandle = Sig('in')
    GrabAllHandles = Sig()
    GetAllHandles = Sig('in', 'buf[256]')
    GetHandleBySerial = Sig('in')
    ReleaseHandle = Sig('in')
    ReleaseAllHandles = Sig()

    class Device(NiceObject):
        handle_last = True
        _init_ = 'InitHandle'

        DeviceAttached = Sig('in', 'in')
        GetCalibration = Sig('in', 'in')
        GetFirmwareVersion = Sig('inout', 'inout', 'in')
        PrintDeviceInfo = Sig('in')
        GetSerialNumber = Sig('in')

        SingleReadN = Sig('in', 'in')
        SingleWriteN = Sig('out', 'in', 'in')
        MonitorN = Sig('in', 'in', 'in')
        GetCommandedPosition = Sig('inout', 'inout', 'inout', 'in')


if __name__ == '__main__':
    print(NiceNanodrive.DLLVersion(0, 0))
    device = NiceNanodrive.Device()

    print(device.GetSerialNumber())
    print(f'Axis X range: {device.GetCalibration(1)} µm')
    print(f'Axis Y range: {device.GetCalibration(2)} µm')
    print(f'Axis Z range: {device.GetCalibration(3)} µm')
    print(device.GetFirmwareVersion(0, 0))
    device.PrintDeviceInfo()
