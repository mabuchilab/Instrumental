from nicelib import load_lib, generate_bindings, NiceLib, Sig, RetHandler, ret_return, NiceObject
from instrumental.errors import Error, TimeoutError


class TLPMError(Error):
    def __init__(self, code):
        for key in NiceTLPM._defs:
            if 'ERROR' in key and NiceTLPM._defs[key] == code:
                msg = f"({code}) {key}"
                self.code = code
                super().__init__(msg)
                break


@RetHandler(num_retvals=0)
def ret_errcheck(ret):
    """Check error code, ignoring void functions"""
    if ret != NiceTLPM._defs['VI_SUCCESS']:
        raise(TLPMError(ret))


def get_0_handle():
    return 0


class NiceTLPM(NiceLib):
    _info_ = load_lib('tlpm', __package__)
    _ret_ = ret_errcheck
    _prefix_ = 'TLPM_'
    _buflen_ = 256

    init = Sig('in', 'in', 'in', 'out')
    close = Sig('in')

    class Rsrc(NiceObject):
        _init_ = get_0_handle
        _buflen_ = 256

        use_handle = False
        findRsrc = Sig('in', 'out')
        getRsrcName = Sig('in', 'in', 'bufout')
        getRsrcInfo = Sig('in', 'in', 'bufout', 'bufout', 'bufout', 'out')

    class Device(NiceObject):
        _init_ = 'init'
        reset = Sig('in')


if __name__ == '__main__':
    version = NiceTLPM.findRsrc()
