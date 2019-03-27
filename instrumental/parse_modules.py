# -*- coding: utf-8 -*-
# Copyright 2017-2019 Nate Bogdanowicz
from __future__ import unicode_literals
from future.utils import PY2

import io
import os
import os.path
import sys
import ast
import datetime as dt
import logging as log
import tokenize as _tokenize

THIS_DIR = os.path.dirname(__file__) or os.path.curdir
sys.path[0:0] = [THIS_DIR]
import std_modules

if PY2:
    tokenize = _tokenize.generate_tokens
else:
    tokenize = _tokenize.tokenize


IGNORED_IMPORTS = ['numpy', 'scipy', 'pint', 'future', 'past']
VAR_NAMES = ['_INST_PARAMS', '_INST_PRIORITY', '_INST_CLASSES', '_INST_VISA_INFO']
DVAR_NAMES = [v+'_' for v in VAR_NAMES]
DEFAULT_VALUES = {
    '_INST_PARAMS': [],
    '_INST_PRIORITY': 5,
    '_INST_CLASSES': [],
    '_INST_VISA_INFO': {},
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


def get_submodules(root_dir):
    """Yield the relpaths of all non-underscored python files nested within root_dir"""
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            if not filename.startswith('_') and filename.endswith('.py'):
                yield os.path.join(root, filename)


def analyze_file(fpath):
    """Parse special vars and imports from the given python source file"""
    print('Parsing {}'.format(fpath))
    with io.open(fpath, 'rb') as f:
        source = f.read()
    root = ast.parse(source)
    has_special_vars, values = get_module_level_special_vars(fpath, root)
    requirements = get_imports(source, root)

    # TODO: Make per-class priority, params, etc. (maybe)
    caf = ClassAttrFinder(root, fpath)
    print(caf.class_info)
    if caf.has_class_vars:
        if has_special_vars:
            raise ValueError("Can't mix module-level and class-level special INSTR vars")
        classes = []
        params = set()
        priority = 5
        visa_info = {}
        for classname, vars in caf.class_info.items():
            if not vars:
                continue
            classes.append(classname)
            params = params.union(vars.get('_INST_PARAMS_', ()))
            priority = max(priority, vars.get('_INST_PRIORITY_', 5))
            if '_INST_VISA_INFO_' in vars:
                visa_info[classname] = vars['_INST_VISA_INFO_']
        values['_INST_CLASSES'] = classes
        values['_INST_PARAMS'] = list(params)
        values['_INST_PRIORITY'] = priority
        values['_INST_VISA_INFO'] = visa_info or None
        has_special_vars = True

    values['nonstd_imports'] = filter_std_modules(requirements)
    return has_special_vars, values


def special_file_info(root_dir):
    """Yield (path_list, vars) pairs of special vars for each .py file nested within root_dir"""
    for fpath in get_submodules(root_dir):
        has_vars, vars = analyze_file(fpath)
        if has_vars:
            relpath = os.path.relpath(fpath, start=root_dir)
            relpath_no_ext, _ = os.path.splitext(relpath)
            path_list = os.path.normpath(relpath_no_ext).split(os.path.sep)
            yield path_list, vars


def driver_special_info():
    """Get info from driver submodules, including nested ones"""
    info = {}
    drivers_dir = os.path.join(THIS_DIR, 'drivers')
    for path_list, vars in special_file_info(drivers_dir):
        if len(path_list) < 2:
            continue
        driver_module = '.'.join(path_list)
        info[driver_module] = vars
    return info


def driver_special_info_squashed():
    """Get info from driver submodules, consolidating sub-submodules (even underscored ones)"""
    info = {}
    drivers_dir = os.path.join(THIS_DIR, 'drivers')
    for path_list, vars in special_file_info(drivers_dir):
        if len(path_list) < 2:
            continue
        category, driver = path_list[:2]
        driver_str = category + '.' + driver.strip('_')

        old_vars = info.setdefault(driver_str, {})
        add_driver_info(old_vars, vars)
    return info


def add_driver_info(old, new):
    """Update one _INST_ dict from another"""
    combine_sorted(old.setdefault('_INST_CLASSES', []), new['_INST_CLASSES'])
    combine_sorted(old.setdefault('_INST_PARAMS', []), new['_INST_PARAMS'])
    old['_INST_PRIORITY'] = max(old.get('_INST_PRIORITY', 5), new['_INST_PRIORITY'])
    combine_sorted(old.setdefault('nonstd_imports', []), new['nonstd_imports'])

    if '_INST_VISA_INFO_' in new:
        visa_info = old.setdefault('INST_VISA_INFO', {})
        visa_info.update(new['_INST_VISA_INFO'])


def combine_sorted(old, new):
    combined = set(old) | set(new)
    old[:] = sorted(combined)


def get_subclass_tree():
    base = []
    for cat_name in os.listdir(os.path.join(THIS_DIR, 'drivers')):
        category_path = os.path.join(THIS_DIR, 'drivers', cat_name)
        if not category_path.is_dir() or cat_name.startswith('_'):
            continue

        cat_info_list = get_subclasses_of('Instrument', cat_name)

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
    with io.open(os.path.join(THIS_DIR, 'drivers', outer, inner+'.py'), 'rb') as f:
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


def get_module_level_special_vars(module_name, root):
    has_special_vars = False
    values = DEFAULT_VALUES.copy()

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
    return has_special_vars, values


def get_imports(source, root):
    imported_modules = []
    linenos = []
    for node in root.body:
        if isinstance(node, ast.Import):
            imported_modules.extend(n.name for n in node.names)
            linenos.extend([node.lineno]*len(node.names))
        elif isinstance(node, ast.ImportFrom):
            # Ignore dot-prefixed imports
            if node.level == 0:
                imported_modules.append(node.module)
                linenos.append(node.lineno)
        else:
            continue

    requirements = []
    tokens = tokenize(io.BytesIO(source).readline)
    for mod_name, lineno in zip(imported_modules, linenos):
        if mod_name is not None:
            requirement = mod_name.split('.', 1)[0]
            comment = get_line_comment(tokens, lineno)
            if comment:
                chunks = comment[1:].split(':')
                if chunks[0].strip() == 'req':
                    requirement = chunks[1].strip()
            requirements.append(requirement)
    return requirements


def parse_driver_modules(module_name):
    driver_dir = os.path.join(THIS_DIR, 'drivers', *(module_name.split('.')))
    for fname in os.listdir(driver_dir):
        if fname.endswith('.py') and not fname.startswith('_'):
            mod_name = fname[:-3]
            yield group + '.' + mod_name


def parse_driver_modules(module_name):
    """Parse special vars and imports from the given driver module"""
    source = load_module_source(module_name)
    root = ast.parse(source)
    has_special_vars, values = get_module_level_special_vars(module_name, root)
    requirements = get_imports(source, root)

    # TODO: Make per-class priority, params, etc. (maybe)
    caf = ClassAttrFinder(root, 'instrumental.drivers.' + module_name)
    if caf.has_class_vars:
        if has_special_vars:
            raise ValueError("Can't mix module-level and class-level special INSTR vars")
        classes = []
        params = set()
        priority = 5
        visa_info = {}
        for classname, vars in caf.class_info.items():
            if not vars:
                continue
            classes.append(classname)
            params = params.union(vars.get('_INST_PARAMS_', ()))
            priority = max(priority, vars.get('_INST_PRIORITY_', 5))
            if '_INST_VISA_INFO_' in vars:
                visa_info[classname] = vars['_INST_VISA_INFO_']
        values['_INST_CLASSES'] = classes
        values['_INST_PARAMS'] = list(params)
        values['_INST_PRIORITY'] = priority
        values['_INST_VISA_INFO'] = visa_info
        has_special_vars = True

    values['nonstd_imports'] = filter_std_modules(requirements)
    return has_special_vars, values


def get_line_comment(tokens, lineno):
    """Get the comment on a given line.

    Returns the text of the comment on a given line, or None if there is no comment. If the
    statement starting on that line spans multiple lines, the last of the comments is used.
    """
    comment = None
    while True:
        token = next(tokens)
        token_type, token_string, token_start, _, _ = token  # Py2 doesn't use namedtuple
        if token_start[0] < lineno:
            continue
        if token_type is _tokenize.COMMENT:
            comment = token_string
        elif token_type is _tokenize.NEWLINE:
            break
    return comment


def generate_info_file():
    num_missing = 0
    mod_info = []
    for module_name, values in driver_special_info().items():
        #has_special_vars, values = parse_driver_modules(module_name)
        mod_info.append((values['_INST_PRIORITY'], module_name, values))
        #if not has_special_vars:
        #    num_missing += 1
        #    print("Module '{}' is missing its '_INST_*' variables".format(module_name))
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
            params = sorted(values['_INST_PARAMS'])
            classes = sorted(values['_INST_CLASSES'])
            nonstd_imports = sorted(values['nonstd_imports'])
            f.write("    ({!r}, {{\n".format(module_name))
            f.write("        'params': {!r},\n".format(params))
            f.write("        'classes': {!r},\n".format(classes))
            f.write("        'imports': {!r},\n".format(nonstd_imports))

            if params and 'visa_address' in params:
                visa_info = values.get('_INST_VISA_INFO')
                if not visa_info:
                    f.write("        'visa_info': {},\n")
                else:
                    f.write("        'visa_info': {\n")
                    for key in sorted(visa_info.keys()):
                        f.write("            {!r}: {!r},\n".format(key, visa_info[key]))
                    f.write("        },\n")

            f.write('    }),\n')
        f.write('])\n')


class ClassAttrFinder(ast.NodeVisitor):
    """A NodeVisitor to find special _INSTR_ class attributes"""
    def __init__(self, tree, module):
        self.ns = {}
        self.class_info = {}
        self.has_class_vars = False
        self.module = module
        self.visit(tree)

    def visit_Import(self, node):
        for alias in node.names:
            self.ns[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if node.module:
                module_parts = node.module.split('.')
            else:
                module_parts = self.module.split('.')[:-node.level]
            self.ns[alias.asname or alias.name] = '.'.join(module_parts + [alias.name])

    def visit_ClassDef(self, node):
        info = self.class_info[node.name] = {}
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        attr_name = target.id
                        if attr_name in DVAR_NAMES:
                            info[attr_name] = ast.literal_eval(stmt.value)
                            self.has_class_vars = True


if __name__ == '__main__':
    generate_info_file()
