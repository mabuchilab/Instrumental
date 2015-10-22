from cffi import FFI

ffi = FFI()
ffi.set_source('errortext', """
    #define PCO_ERR_H_CREATE_OBJECT
    #define PCO_ERRT_H_CREATE_OBJECT
    #include <windows.h>
    #include "PCO_errt.h"
""")
ffi.cdef("void PCO_GetErrorText(DWORD dwerr, char* pbuf, DWORD dwlen);")

if __name__ == '__main__':
    ffi.compile()
