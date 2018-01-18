# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import modify_pattern

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
typedef unsigned char byte;

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


def ref_hook(tokens):
    return modify_pattern(tokens, [('k', 'int64_t'), ('d', '&'), ('a', '*'),
                                   ('k', 'lastUpdateTimeMS')])


def scc_hook(tokens):
    """Fixes a (seeming) typo in the ISC header"""
    for token in tokens:
        if token.string == 'SCC_RequestJogParams':
            token.string = 'ISC_RequestJogParams'
        yield token


def build():
    build_lib(header_info, lib_names, '_kinesislib', __file__, ignore_system_headers=True,
              preamble=preamble, hook_groups='C++', token_hooks=(ref_hook, scc_hook))


if __name__ == '__main__':
    build()
