# -*- coding: utf-8 -*-
# Copyright 2013-2017 Nate Bogdanowicz


import sys
from types import ModuleType

from pint import _DEFAULT_REGISTRY

from .__about__ import (__author__, __copyright__, __email__, __license__, __distname__, __url__,
                        __version__)

# Use the default UnitRegistry instance for the entire package
u = _DEFAULT_REGISTRY
Q_ = u.Quantity


# NOTE: Lazy-loading code from (http://github.com/mitsuhiko/werkzeug)
#
# Lazy loading allows us to have a nice flat api so we can do things like
# `from instrumental import fit_scan` rather than using subpackages.
# If we just imported these directly in this toplevel __init__.py,
# we'd end up always importing everything, which could take awhile.
# Lazy loading lets us load only what we need, when we need it.

# Import mapping to objects in other modules
all_by_module = {
    'instrumental.fitting': ['guided_trace_fit', 'guided_ringdown_fit'],
    'instrumental.drivers': ['instrument', 'list_instruments',
                             'list_visa_instruments', 'saved_instruments'],
    'instrumental.tools': ['fit_scan', 'fit_ringdown'],
    'instrumental.conf': ['load_config_file']
}

# Modules that should be imported when accessed as attributes of instrumental
attribute_modules = frozenset(['appdirs', 'conf', 'plotting'])

# Compute the reverse mappings: from objects to their modules
object_origins = {}
for module, items in all_by_module.items():
    for item in items:
        object_origins[item] = module


class module(ModuleType):
    """Automatically import objects from the modules."""

    def __getattr__(self, name):
        if name in object_origins:
            module = __import__(object_origins[name], None, None, [name])
            for extra_name in all_by_module[module.__name__]:
                setattr(self, extra_name, getattr(module, extra_name))
            return getattr(module, name)
        elif name in attribute_modules:
            __import__('instrumental.' + name)
        return ModuleType.__getattribute__(self, name)

    def __dir__(self):
        """Just show what we want to show."""
        result = list(new_module.__all__)
        result.extend(('__file__', '__path__', '__doc__', '__all__',
                       '__docformat__', '__name__', '__path__',
                       '__package__', '__version__'))
        return result

# Keep a reference to this module so that it's not garbage collected
old_module = sys.modules['instrumental']

# Setup the new module and patch it into the dict of loaded modules
# Make sure to include all existing variables you want to copy over
new_module = sys.modules['instrumental'] = module('instrumental')
new_module.__dict__.update({
    '__file__': __file__,
    '__package__': 'instrumental',
    '__path__': __path__,
    '__doc__': __doc__,
    '__version__': __version__,
    '__all__': tuple(object_origins) + tuple(attribute_modules),
    '__docformat__': 'restructuredtext en',
    'u': u,
    'Q_': Q_
})
