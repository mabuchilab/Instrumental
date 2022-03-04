# -*- coding: utf-8 -*-
"""
Created the 03/03/2022

@author: Sebastien Weber
"""

from nicelib import load_lib, NiceLib, Sig, RetHandler, ret_return, NiceObject, ret_ignore
from instrumental.errors import Error, TimeoutError


class NiceNanoDriveError(Error):
    def __init__(self, code):
        for key in NiceNanodrive._defs:
            if NiceNanodrive._defs[key] == code:
                super().__init__(key)
                break


def get_device_index(index):
    return index


def get_device_channel_index(dev_index, channel_index):
    return dev_index, channel_index


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret is not None:
        if ret < 0:
            raise(NiceNanoDriveError(int(ret)))
        else:
            return ret


def init_device(serial=None):
    if serial is None:
        return NiceNanodrive.InitHandle()
    else:
        return NiceNanodrive.GetHandleBySerial(serial)


class NiceNanodrive(NiceLib):
    _info_ = load_lib('nanodrive', __package__)
    _ret_ = ret_errcheck
    _prefix_ = 'MCL_'
    _buflen_ = 128

    DLLVersion = Sig('inout', 'inout', ret=ret_ignore)

    InitHandle = Sig()
    GrabHandle = Sig('in')
    GrabAllHandles = Sig()
    GetAllHandles = Sig('arr', 'len=10')
    GetHandleBySerial = Sig('in')
    GetSerialNumber = Sig('in')

    ReleaseAllHandles = Sig(ret=ret_ignore)

    class Device(NiceObject):
        handle_last = True
        _init_ = 'GetHandleBySerial'

        ReleaseHandle = Sig('in', ret=ret_ignore)

        DeviceAttached = Sig('in', 'in')
        GetCalibration = Sig('in', 'in')
        GetFirmwareVersion = Sig('inout', 'inout', 'in')
        PrintDeviceInfo = Sig('in', ret=ret_ignore)
        GetSerialNumber = Sig('in')

        SingleReadN = Sig('in', 'in')
        SingleWriteN = Sig('in', 'in', 'in')
        MonitorN = Sig('in', 'in', 'in')
        GetCommandedPosition = Sig('inout', 'inout', 'inout', 'in')




if __name__ == '__main__':
    try:

        print(NiceNanodrive.DLLVersion(0, 0))

        NiceNanodrive.GrabAllHandles()
        handles, Nhandles = NiceNanodrive.GetAllHandles()
        serials = []
        for ind in range(Nhandles):
            serials.append(NiceNanodrive.GetSerialNumber(handles[ind]))

        NiceNanodrive.ReleaseAllHandles()

        NiceNanodrive.GrabAllHandles()
        device = NiceNanodrive.Device(serials[0])

        print(device.GetSerialNumber())
        print(f'Axis X range: {device.GetCalibration(1)} µm')
        print(f'Axis Y range: {device.GetCalibration(2)} µm')
        #print(f'Axis Z range: {device.GetCalibration(3)} µm')
        print(device.GetFirmwareVersion(0, 0))
        device.PrintDeviceInfo()

        print(f'Position of axis 1:{device.SingleReadN(1)} µm')
        print(f'Position of axis 2:{device.SingleReadN(2)} µm')

        device.SingleWriteN(10.5, 1)
        device.SingleWriteN(20.5, 2)

        print(f'Position of axis 1:{device.SingleReadN(1)} µm')
        print(f'Position of axis 2:{device.SingleReadN(2)} µm')

        print(f'Position of axis 1:{device.MonitorN(15.6, 1)} µm')
        print(f'Position of axis 2:{device.MonitorN(31.7, 2)} µm')

    except NiceNanoDriveError as e:
        print(e)
    finally:
        device.ReleaseAllHandles()
