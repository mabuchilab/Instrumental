import os.path
from cffi import FFI

ffi = FFI()
ffi.set_source('instrumental.drivers.cameras._pixelfly.errortext', """
    #define PCO_ERR_H_CREATE_OBJECT
    #define PCO_ERRT_H_CREATE_OBJECT
    #include <windows.h>
    #include "PCO_errt.h"
""", include_dirs=[os.path.dirname(__file__)])
ffi.cdef("void PCO_GetErrorText(DWORD dwerr, char* pbuf, DWORD dwlen);")

if __name__ == '__main__':
    ffi.compile()
