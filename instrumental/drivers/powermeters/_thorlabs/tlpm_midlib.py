# -*- coding: utf-8 -*-
# Author Sebastien Weber
# Date 2022/03/07

from nicelib import load_lib, generate_bindings, \
    NiceLib, Sig, RetHandler, ret_return, NiceObject, ret_ignore
from instrumental.errors import Error, TimeoutError


class TLPMError(Error):
    def __init__(self, msg):
        super().__init__(msg)


@RetHandler(num_retvals=0)
def ret_errcheck(ret, niceobj):
    """Check error code, ignoring void functions"""
    if ret != NiceTLPM._defs['VI_SUCCESS']:
        message = niceobj.errorMessage(ret).decode()
        raise(TLPMError(message))


def get_0_handle():
    return 0


class NiceTLPM(NiceLib):
    _info_ = load_lib('tlpm', __package__)
    _ret_ = ret_errcheck
    _prefix_ = 'TLPM_'
    _buflen_ = 256

    init = Sig('in', 'in', 'in', 'out')
    close = Sig('in',ret=ret_ignore)

    class Rsrc(NiceObject):
        _init_ = get_0_handle
        use_handle = False
        findRsrc = Sig('in', 'out')
        getRsrcName = Sig('in', 'in', 'buf[256]')
        getRsrcInfo = Sig('in', 'in', 'buf[256]', 'buf[256]', 'buf[256]', 'out')
        errorMessage = Sig('in', 'in', 'buf[512]')

    class Powermeter(NiceObject):
        _init_ = 'init'

        findRsrc = Sig('in', 'out')
        getRsrcName = Sig('in', 'in', 'buf[256]')
        getRsrcInfo = Sig('in', 'in', 'buf[256]', 'buf[256]', 'buf[256]', 'out')

        reset = Sig('in')
        errorMessage = Sig('in', 'in', 'buf[512]')
        getCalibrationMsg = Sig('in', 'buf[256]')
        close = Sig('in')

        getAvgTime = Sig('in', 'in', 'out')
        setAvgTime = Sig('in', 'in')

        getWavelength = Sig('in', 'in', 'out')
        setWavelength = Sig('in', 'in')

        setPowerAutoRange = Sig('in', 'in')
        getPowerAutorange = Sig('in', 'out')

        setPowerRange = Sig('in', 'in')
        getPowerRange = Sig('in', 'in', 'out')

        getPowerUnit = Sig('in', 'out')
        setPowerUnit = Sig('in', 'in')

        measPower = Sig('in', 'out')



if __name__ == '__main__':
    rsrc = NiceTLPM.Rsrc()
    Nrsrc = rsrc.findRsrc()
    name = rsrc.getRsrcName(0).decode()
    print(f'The selected ressource is {name}')
    model, serial, manufact, available = rsrc.getRsrcInfo(0)
    NiceTLPM.close(0)

    powermeter = NiceTLPM.Powermeter(name.encode(), 1, 1)
    print(f'The calibration has been done the {powermeter.getCalibrationMsg().decode()}')
    pass
    powermeter.close()
