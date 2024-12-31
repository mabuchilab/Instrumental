import sys
import os.path
import setuptools  # Fix distutils issues
from cffi import FFI

ffi = FFI()
mod_name = 'instrumental.drivers.cameras._pixelfly.errortext'

if sys.platform.startswith('win'):
    ffi.set_source(mod_name, """
        #define PCO_ERR_H_CREATE_OBJECT
        #define PCO_ERRT_H_CREATE_OBJECT
        #include <windows.h>
        #include "PCO_errt.h"
    """, include_dirs=[os.path.dirname(__file__)])
    ffi.cdef("void PCO_GetErrorText(DWORD dwerr, char* pbuf, DWORD dwlen);")
else:
    ffi.set_source(mod_name, '')

if __name__ == '__main__':
    ffi.compile()
