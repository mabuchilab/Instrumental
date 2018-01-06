# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
from nicelib import build_lib

header_info = {
    'win*': {
        'path': (
            r"{PROGRAMFILES}\Thorlabs\Kinesis",
            r"{PROGRAMFILES(X86)}\Thorlabs\Kinesis",
        ),
        'header': 'Thorlabs.MotionControl.IntegratedStepperMotors.h'
    },
}

lib_names = {'win*': 'Thorlabs.MotionControl.IntegratedStepperMotors.dll'}

preamble = """
typedef struct tagSAFEARRAYBOUND {
  ULONG cElements;
  LONG  lLbound;
} SAFEARRAYBOUND, *LPSAFEARRAYBOUND;

typedef struct tagSAFEARRAY {
  USHORT         cDims;
  USHORT         fFeatures;
  ULONG          cbElements;
  ULONG          cLocks;
  PVOID          pvData;
  SAFEARRAYBOUND rgsabound[1];
} SAFEARRAY, *LPSAFEARRAY;
"""

def build():
    build_lib(header_info, lib_names, '_kinesislib', __file__, ignore_system_headers=True,
              preamble=preamble, hook_groups='C++')


if __name__ == '__main__':
    build()
