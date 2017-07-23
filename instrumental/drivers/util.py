# -*- coding: utf-8 -*-
# Copyright 2015-2017 Nate Bogdanowicz
"""
Helpful utilities for writing drivers.
"""
import contextlib
from inspect import getargspec
import pint

from past.builtins import basestring

from . import decorator
from .. import Q_, u

__all__ = ['check_units', 'unit_mag', 'check_enums', 'as_enum', 'visa_timeout_context']


def as_enum(enum_type, arg):
    """Check if arg is an instance or key of enum_type, and return that enum"""
    if isinstance(arg, enum_type):
        return arg
    try:
        return enum_type[arg]
    except KeyError:
        raise ValueError("{} is not a valid {} enum".format(arg, enum_type.__name__))


def check_units(*pos, **named):
    """Decorator to enforce the dimensionality of input args and return values.

    Allows strings and anything that can be passed as a single arg to `pint.Quantity`.
    ::
        @check_units(value='V')
        def set_voltage(value):
            pass  # `value` will be a pint.Quantity with Volt-like units
    """
    def inout_map(arg, unit_info, name=None):
        if unit_info is None:
            return arg

        optional, units = unit_info
        if optional and arg is None:
            return None
        elif arg == 0:
            # Allow naked zeroes as long as we're using absolute units (e.g. not degF)
            # It's a bit dicey using this private method; works in 0.6 at least
            if units._ok_for_muldiv():
                return Q_(arg, units)
            else:
                if name is not None:
                    raise pint.DimensionalityError(u.dimensionless.units, units.units,
                                                   extra_msg=" for argument '{}'".format(name))
                else:
                    raise pint.DimensionalityError(u.dimensionless.units, units.units,
                                                   extra_msg=" for return value")
        else:
            q = Q_(arg)
            if q.dimensionality != units.dimensionality:
                if name is not None:
                    raise pint.DimensionalityError(q.units, units.units,
                                                   extra_msg=" for argument '{}'".format(name))
                else:
                    raise pint.DimensionalityError(q.units, units.units,
                                                   extra_msg=" for return value")
            return q

    return _unit_decorator(inout_map, inout_map, pos, named)


def unit_mag(*pos, **named):
    """Decorator to extract the magnitudes of input args and return values.

    Allows strings and anything that can be passed as a single arg to `pint.Quantity`.
    ::
        @unit_mag(value='V')
        def set_voltage(value):
            pass  # The input must be in Volt-like units and `value` will be a raw number
                  # expressing the magnitude in Volts
    """
    def in_map(arg, unit_info, name):
        if unit_info is None:
            return arg

        optional, units = unit_info
        if optional and arg is None:
            return None
        elif arg == 0:
            # Allow naked zeroes as long as we're using absolute units (e.g. not degF)
            # It's a bit dicey using this private method; works in 0.6 at least
            if units._ok_for_muldiv():
                return arg
            else:
                if name is not None:
                    raise pint.DimensionalityError(u.dimensionless.units, units.units,
                                                   extra_msg=" for argument '{}'".format(name))
                else:
                    raise pint.DimensionalityError(u.dimensionless.units, units.units,
                                                   extra_msg=" for return value")
        else:
            q = Q_(arg)
            try:
                return q.to(units).magnitude
            except pint.DimensionalityError:
                raise pint.DimensionalityError(q.units, units.units,
                                               extra_msg=" for argument '{}'".format(name))

    def out_map(res, unit_info):
        if unit_info is None:
            return res

        optional, units = unit_info
        if optional and res is None:
            return None
        else:
            q = Q_(res)
            try:
                return q
            except pint.DimensionalityError:
                raise pint.DimensionalityError(q.units, units.units, extra_msg=" for return value")

    return _unit_decorator(in_map, out_map, pos, named)


def check_enums(**kw_args):
    """Decorator to type-check input arguments as enums.

    Allows strings and anything that can be passed to `~instrumental.drivers.util.as_enum`.
    ::
        @check_enums(mode=SampleMode)
        def set_mode(mode):
            pass  # `mode` will be of type SampleMode
    """
    def checker_factory(enum_type, arg_name):
        def checker(arg):
            return as_enum(enum_type, arg)
        return checker
    return arg_decorator(checker_factory, (), kw_args)


def arg_decorator(checker_factory, dec_pos_args, dec_kw_args):
    """Produces a decorator that checks the arguments to the function in wraps.

    Parameters
    ----------
    checker_factory : function
        Takes the args (decorator_arg_val, arg_name) and produces a 'checker' function, which takes
        and returns a single value. When acting simply as a checker, it takes the arg, checks that
        it is valid (using the ``decorator_arg_val`` and/or ``arg_name``), raises an Exception if
        it is not, and returns the value unchanged if it is. Additionally, the checker may return a
        different value, e.g. a ``str`` which has been converted to a ``Quantity`` as in
        ``check_units()``.
    dec_pos_args : tuple
        The positional args (i.e. *args) passed to the decorator constructor
    dec_kw_args : dict
        The keyword args (i.e. **kwargs) passed to the decorator constructor
    """
    def wrap(func):
        """Function that actually wraps the function to be decorated"""
        arg_names, vargs, kwds, default_vals = getargspec(func)
        default_vals = default_vals or ()
        pos_arg_names = {i: name for i, name in enumerate(arg_names)}

        # Put everything in one dict
        for dec_arg_val, arg_name in zip(dec_pos_args, arg_names):
            if arg_name in dec_kw_args:
                raise TypeError("Argument specified twice, by both position and name")
            dec_kw_args[arg_name] = dec_arg_val

        checkers = {}
        new_defaults = {}
        num_nondefs = len(arg_names) - len(default_vals)
        for default_val, arg_name in zip(default_vals, arg_names[num_nondefs:]):
            if arg_name in dec_kw_args:
                checker = checker_factory(dec_kw_args[arg_name], arg_name)
                checkers[arg_name] = checker
                new_defaults[arg_name] = checker(default_val)

        for arg_name in arg_names[:num_nondefs]:
            if arg_name in dec_kw_args:
                checkers[arg_name] = checker_factory(dec_kw_args[arg_name], arg_name)

        def wrapper(func, *args, **kwds):
            checked = new_defaults.copy()
            checked.update({name: (checkers[name](arg) if name in checkers else arg) for name, arg
                            in kwds.items()})
            for i, arg in enumerate(args):
                name = pos_arg_names[i]
                checked[name] = checkers[name](arg) if name in checkers else arg

            result = func(**checked)
            return result
        return decorator.decorate(func, wrapper)
    return wrap


def _unit_decorator(in_map, out_map, pos_args, named_args):
    def wrap(func):
        ret = named_args.pop('ret', None)

        if ret is None:
            ret_units = None
        elif isinstance(ret, tuple):
            ret_units = []
            for arg in ret:
                if arg is None:
                    unit = None
                elif isinstance(arg, basestring):
                    optional = arg.startswith('?')
                    if optional:
                        arg = arg[1:]
                    unit = (optional, Q_(arg))
                ret_units.append(unit)
            ret_units = tuple(ret_units)
        else:
            optional = ret.startswith('?')
            if optional:
                arg = ret[1:]
            ret_units = Q_(arg)

        arg_names, vargs, kwds, defaults = getargspec(func)

        pos_units = []
        for arg in pos_args:
            if arg is None:
                unit = None
            elif isinstance(arg, basestring):
                optional = arg.startswith('?')
                if optional:
                    arg = arg[1:]
                unit = (optional, Q_(arg))
            else:
                raise TypeError("Each arg spec must be a string or None")
            pos_units.append(unit)

        named_units = {}
        for name, arg in named_args.items():
            if arg is None:
                unit = None
            elif isinstance(arg, basestring):
                optional = arg.startswith('?')
                if optional:
                    arg = arg[1:]
                unit = (optional, Q_(arg))
            else:
                raise TypeError("Each arg spec must be a string or None")
            named_units[name] = unit

        # Add positional units to named units
        for i, units in enumerate(pos_units):
            name = arg_names[i]
            if name in named_units:
                raise Exception("Units of {} specified by position and by name".format(name))
            named_units[name] = units

        # Pad out the rest of the positional units with None
        pos_units.extend([None] * (len(arg_names) - len(pos_args)))

        # Add named units to positional units
        for name, units in named_units.items():
            try:
                i = arg_names.index(name)
                pos_units[i] = units
            except ValueError:
                pass

        defaults = tuple() if defaults is None else defaults

        # Convert the defaults
        new_defaults = {}
        ndefs = len(defaults)
        for d, unit, n in zip(defaults, pos_units[-ndefs:], arg_names[-ndefs:]):
            new_defaults[n] = d if unit is None else in_map(d, unit, n)

        def wrapper(func, *args, **kwargs):
            # Convert the input arguments
            new_args = [in_map(a, u, n) for a, u, n in zip(args, pos_units, arg_names)]
            new_kwargs = {n: in_map(a, named_units.get(n, None), n) for n, a in kwargs.items()}

            # Fill in converted defaults
            for name in arg_names[max(len(args), len(arg_names)-len(defaults)):]:
                if name not in new_kwargs:
                    new_kwargs[name] = new_defaults[name]

            result = func(*new_args, **new_kwargs)

            # Allow for unit checking of multiple return values
            if isinstance(ret_units, tuple):
                return tuple(map(out_map, result, ret_units))
            else:
                return out_map(result, ret_units)
        return decorator.decorate(func, wrapper)
    return wrap


@contextlib.contextmanager
def visa_timeout_context(resource, timeout):
    """Context manager for temporarily setting a visa resource's timeout.
    ::
        with visa_timeout_context(rsrc, 100):
             ...  # `rsrc` will have a timeout of 100 ms within this block
    """
    old_timeout = resource.timeout
    resource.timeout = timeout
    yield
    resource.timeout = old_timeout
