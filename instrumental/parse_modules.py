# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
import re
import os
import os.path
import datetime as dt

from . import std_modules

THIS_DIR = os.path.split(__file__)[0] or '.'
DEFAULT_PRIORITY = 5

RE_IMPORT = re.compile(r"^import[ ]+(\w+)", re.MULTILINE)
RE_FROM_IMPORT = re.compile(r"^from[ ]+([^.][^ ]*)[ ]+import", re.MULTILINE)
RE_PARAMS = re.compile(r"_INST_PARAMS[ ]*=[ ]*(\[[^\]]*\])")
RE_PRIORITY = re.compile(r"_INST_PRIORITY[ ]*=[ ]*(.*)")


def load_module_source(module):
    outer, inner = module.split('.')
    with open(os.path.join(THIS_DIR, 'drivers', outer, inner+'.py')) as f:
        source = f.read()
    return source


def parse_priority(source):
    match = re.search(RE_PRIORITY, source)
    return eval(match.group(1), {}) if match else DEFAULT_PRIORITY


def parse_params(source):
    match = re.search(RE_PARAMS, source)
    return eval(match.group(1), {}) if match else None


def parse_imported_modules(source):
    """Parse the toplevel modules imported by the given driver module"""
    full_modules = re.findall(RE_IMPORT, source) + re.findall(RE_FROM_IMPORT, source)
    modules = [fullpkg.split('.', 1)[0] for fullpkg in full_modules]
    return modules


def get_nonstd_modules(source, ignore=['numpy', 'scipy', 'pint', 'future', 'past']):
    ignore = ignore + std_modules.all
    imported_modules = parse_imported_modules(source)
    nonstd_modules = []
    for module in imported_modules:
        if module not in ignore and module not in nonstd_modules:
            nonstd_modules.append(module)
    return nonstd_modules


def list_drivers():
    for group in driver_groups():
        group_dir = os.path.join(THIS_DIR, 'drivers', group)
        for fname in os.listdir(group_dir):
            if fname.endswith('.py') and not fname.startswith('_'):
                mod_name = fname[:-3]
                source = load_module_source(group + '.' + mod_name)
                yield (group, mod_name, source)


def generate_info_file():
    mod_info = []
    for group, mod_name, source in list_drivers():
        params = parse_params(source)
        priority = parse_priority(source)
        nonstd_modules = get_nonstd_modules(source)
        mod_info.append( (priority, (group, mod_name), params, nonstd_modules) )

    mod_info.sort()

    file_path = os.path.join(THIS_DIR, 'driver_info.py')
    with open(file_path, 'w') as f:
        f.write('# Auto-generated {}\n'.format(dt.datetime.now().isoformat()))
        f.write('from collections import OrderedDict\n\n\n')

        # Write parameters
        f.write('driver_params = OrderedDict([\n')
        for _, mod_tup, params, _ in mod_info:
            if params is not None:
                f.write('    ({!r}, {!r}),\n'.format(mod_tup, params))
        f.write('])\n')

        # Write import info
        f.write('\n')
        f.write('driver_imports = OrderedDict([\n')
        for _, (group, mod), _, nonstd_modules in mod_info:
            f.write("    ('{}.{}', {!r}),\n".format(group, mod, nonstd_modules))
        f.write('])\n')


def driver_groups():
    return [g for g in os.listdir(os.path.join(THIS_DIR, 'drivers'))
            if os.path.isdir(os.path.join(THIS_DIR, 'drivers', g)) and not g.startswith('_')]


if __name__ == '__main__':
    generate_info_file()
