# -*- coding: utf-8 -*-
# Copyright 2016-2018 Nate Bogdanowicz
from nicelib import build_lib
from nicelib.process import modify_pattern


def make_info(lib_name):
    header_info = {
        'win*': {
            'path': (
                r"{PROGRAMFILES}\Thorlabs\Kinesis",
                r"{PROGRAMFILES(X86)}\Thorlabs\Kinesis",
            ),
            'header': '{}.h'.format(lib_name)
        },
    }

    lib_names = {'win*': '{}.dll'.format(lib_name)}

    return header_info, lib_names

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


def build(shortname, sublib):
    ll_module_name = '_kinesis_{}_lib'.format(shortname)
    header_info, lib_names = make_info(sublib)
    build_lib(header_info, lib_names, ll_module_name, __file__, ignore_system_headers=True,
              preamble=preamble, hook_groups='C++', token_hooks=(ref_hook, scc_hook))
