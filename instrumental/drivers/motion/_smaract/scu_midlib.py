from nicelib import load_lib, generate_bindings, NiceLib, Sig, RetHandler, ret_return, NiceObject
from instrumental.errors import Error, TimeoutError


class SmarActError(Error):
    def __init__(self, code):
        for key in NiceSCU._defs:
            if 'ERROR' in key and NiceSCU._defs[key] == code:
                msg = f"({code}) {key}"
                self.code = code
                super().__init__(msg)
                break


def get_device_index(index):
    return index


def get_device_channel_index(dev_index, channel_index):
    return dev_index, channel_index


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret != NiceSCU._defs['SA_OK']:
        raise(SmarActError(ret))


class NiceSCU(NiceLib):
    _info_ = load_lib('scu', __package__)
    _ret_ = ret_errcheck
    _prefix_ = 'SA_'
    _buflen_ = 128

    AddDeviceToInitDevicesList = Sig('in')
    ClearInitDevicesList = Sig()
    GetDLLVersion = Sig('out')
    GetAvailableDevices = Sig('out', 'inout')
    GetNumberOfDevices = Sig('out')
    GetDeviceID = Sig('in', 'out')

    ReleaseDevices = Sig()
    InitDevices = Sig('in')

    class Device(NiceObject):
        _init_ = get_device_index
        GetDeviceFirmwareVersion = Sig('in', 'out')

    class Actuator(NiceObject):
        _init_ = get_device_channel_index
        _n_handles = 2

        GetSensorPresent_S = Sig('in', 'in', 'out')
        GetSensorType_S = Sig('in', 'in', 'out')
        SetSensorType_S = Sig('in', 'in', 'in')

        Stop_S = Sig('in', 'in')
        # for actuators with sensor
        GetPhysicalPositionKnown_S = Sig('in', 'in', 'out')

        GetPosition_S = Sig('in', 'in', 'out')
        GetAngle_S = Sig('in', 'in', 'out', 'out')

        GetScale_S = Sig('in', 'in', 'out', 'out')
        SetScale_S = Sig('in', 'in', 'in', 'in')

        MoveAngleAbsolute_S = Sig('in', 'in', 'in', 'in', 'in')
        MoveAngleRelative_S = Sig('in', 'in', 'in', 'in', 'in')

        MovePositionAbsolute_S = Sig('in', 'in', 'in', 'in')
        MovePositionRelative_S = Sig('in', 'in', 'in', 'in')

        CalibrateSensor_S = Sig('in', 'in')
        MoveToReference_S = Sig('in', 'in', 'in', 'in')
        SetZero_S = Sig('in', 'in')
        GetStatus_S = Sig('in', 'in', 'out')

        # for actuator without sensors
        MoveStep_S = Sig('in', 'in', 'in', 'in', 'in')
        GetAmplitude_S = Sig('in', 'in', 'out')
        SetAmplitude_S = Sig('in', 'in', 'in')


MODES = ['SA_SYNCHRONOUS_COMMUNICATION', 'SA_ASYNCHRONOUS_COMMUNICATION']
OPERATING_MODES = dict(zip(MODES, [NiceSCU._defs[mode] for mode in MODES]))


if __name__ == '__main__':
    version = NiceSCU.GetDLLVersion()
    ids = NiceSCU.GetAvailableDevices(2048)
    NiceSCU.InitDevices(OPERATING_MODES['SA_SYNCHRONOUS_COMMUNICATION'])
    pass
    NiceSCU.ReleaseDevices()