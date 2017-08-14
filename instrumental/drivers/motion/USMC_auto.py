from nicelib import NiceLib, NiceObjectDef


class MyNiceLib(NiceLib):
    # _info = load_lib('mylibname')
    _prefix = 'USMC_'

    # Init = (Str)
    # GetState = (Device, Str)
    # SaveParametersToFlash = (Device)
    # SetCurrentPosition = (Device, Position)
    # GetMode = (Device, Str)
    # SetMode = (Device, Str)
    # GetParameters = (Device, Str)
    # SetParameters = (Device, Str)
    # GetStartParameters = (Device, Str)
    # Start = (Device, DestPos, Speed, Str)
    # Stop = (Device)
    # GetLastErr = (str, len)
    # Close = ()
    # GetEncoderState = (Device, Str)
