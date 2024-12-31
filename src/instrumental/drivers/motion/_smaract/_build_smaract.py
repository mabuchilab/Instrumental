#_build_smaract
# written by Sébastien Weber
# 2021/09/21


from nicelib import build_lib, generate_bindings
from nicelib.process import declspec_hook

header_info = {
    'win*': {
        'path': (
            r"{SYSTEMDRIVE}\SmarAct\SCU\SDK\include",
        ),
        'header': 'SCU3DControl.h'
    },
}

lib_names = {'win*': 'SCU3DControl'}


def build():
    build_lib(header_info, lib_names, '_sculib', __file__, token_hooks=(declspec_hook,))


# def bindings():
#     with open('bindings.py') as f:
#         generate_bindings(header_info, f)


if __name__ == '__main__':
    build()
    #bindings()