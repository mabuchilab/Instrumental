#_build_thorlabs tlpm lib for powermeter using the tlpm library
# written by Sébastien Weber
# 2021/11/29


from nicelib import build_lib, generate_bindings
from nicelib.process import declspec_hook, struct_func_hook
import os


header_info = {
        'win*': {
            'path': (
                r"{VXIPNPPATH64}\Win64\Include",
                r"{VXIPNPPATH}\WinNT\Include",
            ),
            'header': 'TLPM.h'
        },
}

lib_names = {
    'win*:32': ('TLPM_32',),
    'win*:64': ('TLPM_64',),
}

def fastcall_hook(tokens):
    """Removes ``cdecl``, ``_cdecl``, and ``__cdecl``

    Enabled by default.
    """
    for token in tokens:
        if token not in ('__fastcall',):
            yield token

def build():
    build_lib(header_info, lib_names, '_tlpmlib', __file__, token_hooks=(declspec_hook, fastcall_hook), override=True)


# def bindings():
#     with open('bindings.py') as f:
#         generate_bindings(header_info, f)


if __name__ == '__main__':
    build()
    #bindings()