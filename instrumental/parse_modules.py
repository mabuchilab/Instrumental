# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
import os
import os.path
import ast
import datetime as dt
import logging as log

from . import std_modules

THIS_DIR = os.path.split(__file__)[0] or '.'

IGNORED_IMPORTS = ['numpy', 'scipy', 'pint', 'future', 'past']
VAR_NAMES = ['_INST_PARAMS', '_INST_PRIORITY', '_INST_VISA_INFO']
DEFAULT_VALUES = {
    '_INST_PARAMS': [],
    '_INST_PRIORITY': 5,
    '_INST_VISA_INFO': None,
}


def load_module_source(module):
    outer, inner = module.split('.')
    with open(os.path.join(THIS_DIR, 'drivers', outer, inner+'.py')) as f:
        source = f.read()
    return source


def filter_std_modules(imports, ignore=IGNORED_IMPORTS):
    ignore = ignore + std_modules.all
    nonstd_modules = []
    for module in imports:
        if module not in ignore and module not in nonstd_modules:
            nonstd_modules.append(module)
    return nonstd_modules


def driver_groups():
    return [g for g in os.listdir(os.path.join(THIS_DIR, 'drivers'))
            if os.path.isdir(os.path.join(THIS_DIR, 'drivers', g)) and not g.startswith('_')]


def list_drivers():
    for group in driver_groups():
        group_dir = os.path.join(THIS_DIR, 'drivers', group)
        for fname in os.listdir(group_dir):
            if fname.endswith('.py') and not fname.startswith('_'):
                mod_name = fname[:-3]
                yield group + '.' + mod_name


def parse_module(module_name):
    """Parse special vars and imports from the given driver module"""
    source = load_module_source(module_name)
    values = DEFAULT_VALUES.copy()
    root = ast.parse(source)

    assignments = (n for n in root.body if isinstance(n, ast.Assign) and len(n.targets) == 1)
    for assignment in assignments:
        target = assignment.targets[0]
        if isinstance(target, ast.Name):
            var_name = target.id
            if var_name in VAR_NAMES:
                try:
                    values[var_name] = ast.literal_eval(assignment.value)
                except:
                    log.info("Failed to eval value of %s in module '%s'", var_name, module_name)

    imports = []
    for node in root.body:
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            # Ignore dot-prefixed imports
            if node.level == 0:
                imports.append(node.module)
        else:
            continue
    imports = (fullpkg.split('.', 1)[0] for fullpkg in imports if fullpkg is not None)
    values['nonstd_imports'] = filter_std_modules(imports)

    return values


def generate_info_file():
    mod_info = []
    for module_name in list_drivers():
        values = parse_module(module_name)
        mod_info.append((values['_INST_PRIORITY'], module_name, values))
    mod_info.sort()

    file_path = os.path.join(THIS_DIR, 'driver_info.py')
    with open(file_path, 'w') as f:
        f.write('# Auto-generated {}\n'.format(dt.datetime.now().isoformat()))
        f.write('from collections import OrderedDict\n\n')

        # Write parameters
        f.write('driver_info = OrderedDict([\n')
        for _, module_name, values in mod_info:
            params = values['_INST_PARAMS']
            f.write("    ({!r}, {{\n".format(module_name))
            f.write("        'params': {!r},\n".format(params))
            f.write("        'imports': {!r},\n".format(values['nonstd_imports']))

            if params and 'visa_address' in params:
                f.write("        'visa_info': {!r},\n".format(values['_INST_VISA_INFO']))

            f.write('    }),\n')
        f.write('])\n')


if __name__ == '__main__':
    generate_info_file()
