# -*- coding: utf-8 -*-
# Copyright 2017 Nate Bogdanowicz
import os
import os.path
import ast
import datetime as dt
import logging as log

from . import std_modules

THIS_DIR = os.path.dirname(__file__) or os.path.curdir

IGNORED_IMPORTS = ['numpy', 'scipy', 'pint', 'future', 'past']
VAR_NAMES = ['_INST_PARAMS', '_INST_PRIORITY', '_INST_CLASSES', '_INST_VISA_INFO']
DEFAULT_VALUES = {
    '_INST_PARAMS': [],
    '_INST_PRIORITY': 5,
    '_INST_CLASSES': [],
    '_INST_VISA_INFO': None,
}


class ClassInfo(object):
    def __init__(self, name, bases, module, tree):
        self.name = name
        self.bases = bases
        self.module = module
        self.ast = tree
        self.children = []

    def __repr__(self):
        return '<{}.{}: {}>'.format(self.module, self.name, self.children)


def get_subclass_tree():
    base = []
    for cat_name in os.listdir(os.path.join(THIS_DIR, 'drivers')):
        category_path = os.path.join(THIS_DIR, 'drivers', cat_name)
        if not category_path.is_dir() or cat_name.startswith('_'):
            continue
        print(category_path)

        cat_info_list = get_subclasses_of('Instrument', cat_name)
        print(cat_info_list)

        for cat_info in cat_info_list:
            for d_name in os.listdir(category_path):
                if d_name.startswith('_') or not d_name.endswith('.py'):
                    continue
                mod_name = cat_name + '.' + d_name[:-3]
                driver_info_list = get_subclasses_of(cat_info.name, mod_name)
                cat_info.children.extend(driver_info_list)

        # Exclude categories
        base.extend(cat_info_list)
    return base


def parse_subclasses():
    subclasses = []
    for name in os.listdir(os.path.join(THIS_DIR, 'drivers')):
        path = os.path.join(THIS_DIR, 'drivers', name)
        if not os.path.isdir(path) or name.startswith('_'):
            continue
        analyze_driver_category(path)

    return subclasses


def parse_file(path):
    with open(path) as f:
        return ast.parse(f.read())


def analyze_driver_category(path):
    root = parse_file(os.path.join(path, '__init__.py'))
    get_subclasses_of('Instrument', root)


def analyze_driver_module():
    pass


def analyze_driver_class():
    pass


def parse_module2(module_name):
    parts = module_name.split('.')

    if len(parts) == 1:
        category, = parts
        path = os.path.join(THIS_DIR, 'drivers', category, '__init__.py')
    elif len(parts) == 2:
        category, driver = parts
        path = os.path.join(THIS_DIR, 'drivers', category, (driver + '.py'))
    else:
        raise ValueError('Unknown module {}'.format(module_name))

    with open(path) as f:
        return ast.parse(f.read())


def get_subclasses_of(name, module_name):
    root = parse_module2(module_name)
    subclasses = []
    for node in root.body:
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = [base.id for base in node.bases]
        if name in base_names:
            info = ClassInfo(node.name, base_names, module_name, root)
            subclasses.append(info)
    return subclasses


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
    has_special_vars = False

    assignments = (n for n in root.body if isinstance(n, ast.Assign) and len(n.targets) == 1)
    for assignment in assignments:
        target = assignment.targets[0]
        if isinstance(target, ast.Name):
            var_name = target.id
            if var_name in VAR_NAMES:
                try:
                    values[var_name] = ast.literal_eval(assignment.value)
                    has_special_vars = True
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

    return has_special_vars, values


def generate_info_file():
    num_missing = 0
    mod_info = []
    for module_name in list_drivers():
        has_special_vars, values = parse_module(module_name)
        mod_info.append((values['_INST_PRIORITY'], module_name, values))
        if not has_special_vars:
            num_missing += 1
            print("Module '{}' is missing its '_INST_*' variables".format(module_name))
    mod_info.sort()

    print("{} of {} modules are missing their '_INST_*' variables".format(num_missing,
                                                                          len(mod_info)))

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
            f.write("        'classes': {!r},\n".format(values['_INST_CLASSES']))
            f.write("        'imports': {!r},\n".format(values['nonstd_imports']))

            if params and 'visa_address' in params:
                f.write("        'visa_info': {!r},\n".format(values['_INST_VISA_INFO']))

            f.write('    }),\n')
        f.write('])\n')


if __name__ == '__main__':
    generate_info_file()
