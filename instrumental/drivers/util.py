# -*- coding: utf-8 -*-
# Copyright 2015-2016 Nate Bogdanowicz
"""
Helpful utilities for wrapping libraries in Python
"""
import sys
from inspect import getargspec, isfunction
from functools import update_wrapper
import pint
from .. import Q_


def check_enum(enum_type, arg):
    """Checks if arg is an instance or key of enum_type, and returns that enum"""
    return arg if isinstance(arg, enum_type) else enum_type[arg]


def _cffi_wrapper(ffi, func, fname, sig_tup, err_wrap, struct_maker, default_buflen):
    argtypes = ffi.typeof(func).args
    n_expected_inargs = sum('in' in a for a in sig_tup)

    def wrapped(*inargs):
        inargs = list(inargs)

        if len(inargs) != n_expected_inargs:
            message = '{}() takes '.format(fname)
            if n_expected_inargs == 0:
                message += 'no arguments'
            elif n_expected_inargs == 1:
                message += '1 argument'
            else:
                message += '{} arguments'.format(n_expected_inargs)

            message += ' ({} given)'.format(len(inargs))

            raise TypeError(message)

        outargs = []
        args = []
        buflen = None
        for info, argtype in zip(sig_tup, argtypes):
            if 'inout' in info:
                inarg = inargs.pop(0)
                try:
                    inarg_type = ffi.typeof(inarg)
                except TypeError:
                    inarg_type = type(inarg)

                if argtype == inarg_type:
                    arg = inarg  # Pass straight through
                elif argtype.kind == 'pointer' and argtype.item.kind == 'struct':
                    arg = struct_maker(argtype, inarg)
                else:
                    arg = ffi.new(argtype, inarg)
                outargs.append((arg, lambda o: o[0]))
            elif 'in' in info:
                arg = inargs.pop(0)
            elif 'out' in info:
                if argtype.kind == 'pointer' and argtype.item.kind == 'struct':
                    arg = struct_maker(argtype)
                else:
                    arg = ffi.new(argtype)
                outargs.append((arg, lambda o: o[0]))
            elif info.startswith('buf'):
                if len(info) > 3:
                    buflen = int(info[3:])
                else:
                    buflen = self._buflen
                arg = ffi.new('char[]', buflen)
                outargs.append((arg, lambda o: ffi.string(o)))
            elif info == 'len':
                arg = buflen
                buflen = None
            else:
                raise Exception("Unrecognized arg info '{}'".format(info))
            args.append(arg)

        retval = func(*args)
        out_vals = [f(a) for a, f in outargs]

        if err_wrap:
            err_wrap(retval)
        else:
            out_vals.append(retval)

        if not out_vals:
            return None
        elif len(out_vals) == 1:
            return out_vals[0]
        else:
            return tuple(out_vals)

    wrapped.__name__ = fname
    return wrapped


# WARNING uses some stack frame hackery; should probably make use of this syntax optional
class NiceObject(object):
    def __init__(self, n_handles=1):
        self.n_handles = n_handles
        self.doc = None

    def __enter__(self):
        outer_vars = sys._getframe(1).f_locals
        self.doc = outer_vars.pop('__doc__', None)
        self._enter_names = outer_vars.keys()  # Not including __doc__
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        outer_vars = sys._getframe(1).f_locals
        new_doc = outer_vars.pop('__doc__', None)

        exit_names = outer_vars.keys()
        self.names = set(exit_names).difference(set(self._enter_names))

        if new_doc:
            outer_vars['__doc__'] = self.doc  # Put old var back
        self.doc = new_doc

    def __str__(self):
        return str(self.names)

    def __repr__(self):
        return repr(self.names)


class LibMeta(type):
    def __new__(metacls, clsname, bases, classdict):
        mro_lookup = metacls._create_mro_lookup(classdict, bases)

        ffi = classdict['_ffi']
        lib = classdict['_lib']
        defs = mro_lookup('_defs')
        prefixes = classdict['_prefix']
        err_wrap = classdict['_err_wrap']
        struct_maker = mro_lookup('_struct_maker') or (ffi.new if ffi else None)
        buflen = mro_lookup('_buflen')

        # Add default empty prefix
        if isinstance(prefixes, basestring):
            prefixes = (prefixes, '')
        else:
            prefixes = tuple(prefixes) + ('',)

        niceobjects = {}  # name: NiceObject
        for name, value in classdict.items():
            if isinstance(value, NiceObject):
                value.names.remove(name)  # Remove self
                niceobjects[name] = value

        funcs = {}

        for name, value in classdict.items():
            if (not name.startswith('_') and not isfunction(value) and
                    not isinstance(value, NiceObject)):
                sig_tup = value
                flags = {}

                if not isinstance(sig_tup, tuple):
                    sig_tup = (sig_tup,)

                # Pop off the flags dict
                if sig_tup and isinstance(sig_tup[-1], dict):
                    flags.update(sig_tup[-1])
                    sig_tup = sig_tup[:-1]

                # Try prefixes until we find the lib function
                for prefix in prefixes:
                    ffi_func = getattr(lib, prefix + name, None)
                    if ffi_func is not None:
                        break

                if ffi_func is None:
                    raise AttributeError("No lib function found with a name ending in '{}', with "
                                         "any of these prefixes: {}".format(name, prefixes))

                func = _cffi_wrapper(ffi, ffi_func, name, sig_tup, err_wrap, struct_maker, buflen)

                # Save for use by niceobjs
                funcs[name] = func

                # HACK to get nice repr
                repr_str = metacls._func_repr_str(ffi, func)
                classdict[name] = LibFunction(func, repr_str)

        for cls_name, niceobj in niceobjects.items():
            # Need to use a separate function so we have a per-class closure
            classdict[cls_name] = metacls._create_object_class(cls_name, niceobj, ffi, funcs)
        return super(LibMeta, metacls).__new__(metacls, clsname, bases, classdict)

    @classmethod
    def _create_object_class(metacls, cls_name, niceobj, ffi, funcs):
        repr_strs = {}
        for func_name in niceobj.names:
            repr_strs[func_name] = metacls._func_repr_str(ffi, funcs[func_name],
                                                          niceobj.n_handles)

        def __init__(self, *handles):
            if len(handles) != niceobj.n_handles:
                raise TypeError("__init__() takes exactly {} arguments "
                                "({} given)".format(niceobj.n_handles, len(handles)))

            # Generate "bound methods"
            for func_name in niceobj.names:
                lib_func = LibFunction(funcs[func_name], repr_strs[func_name], handles)
                setattr(self, func_name, lib_func)

        niceobj_dict = {'__init__': __init__, '__doc__': niceobj.doc}
        return type(cls_name, (object,), niceobj_dict)

    @staticmethod
    def _create_mro_lookup(classdict, bases):
        """Generate a lookup function that will search the base classes for an attribute. This
        only searches the mro of the first base, which is OK since you should probably inherit only
        from NiceLib anyway. If there's a use case where multiple inheritance becomes useful, we
        can add the proper mro algorithm here, but that seems unlikely. In fact, even this seems
        like overkill...
        """
        dicts = (classdict,) + tuple(C.__dict__ for C in bases[0].__mro__)
        def lookup(name):
            for d in dicts:
                try:
                    return d[name]
                except KeyError:
                    pass
            raise KeyError(name)
        return lookup

    @staticmethod
    def _func_repr_str(ffi, func, n_handles=0):
        argtypes = ffi.typeof(func._ffi_func).args

        if n_handles > len(func._sig_tup):
            raise ValueError("Signature for function '{}' is missing its required "
                             "handle args".format(func.__name__))

        in_args = [a.cname for a, d in zip(argtypes, func._sig_tup) if 'in' in d][n_handles:]
        out_args = [a.item.cname for a, d in zip(argtypes, func._sig_tup)
                    if ('out' in d or 'buf' in d)]

        if not out_args:
            out_args = ['None']

        repr_str = "{}({}) -> {}".format(func.__name__, ', '.join(in_args), ', '.join(out_args))
        return repr_str


class LibFunction(object):
    def __init__(self, func, repr_str, handles=()):
        self.__name__ = func.__name__
        self._func = func
        self._repr = repr_str
        self._handles = handles

    def __call__(self, *args):
        return self._func(*(self._handles + args))

    def __str__(self):
        return self._repr

    def __repr__(self):
        return self._repr


class NiceLib(object):
    """Base class for mid-level library wrappers

    Provides a nice interface for quickly defining mid-level library wrappers. You define your own
    subclass for each specific library (DLL), then create an instance for each instance of your
    Instrument subclass. See the examples in the developer docs for more info.

    Attributes
    ----------
    _ffi
        FFI instance variable. Required.
    _lib
        FFI library opened with `dlopen()`. Required.
    _prefix : str, optional
        Prefix to strip from the library function names. E.g. If the library has functions named
        like ``SDK_Func()``, you can set `_prefix` to ``'SDK_'``, and access them as `Func()`.
    _err_wrap : function, optional
        Wrapper function to handle error codes returned by each library function.
    _struct_maker : function, optional
        Function that is called to create an FFI struct of the given type. Mainly useful for
        odd libraries that require you to always fill out some field of the struct, like its size
        in bytes (I'm looking at you PCO...)
    _buflen : int, optional
        The default length for buffers. This can be overridden on a per-argument basis in the
        argument's spec string, e.g `'buf64'` will make a 64-byte buffer.
    """
    __metaclass__ = LibMeta
    _ffi = None  # MUST be filled in by subclass
    _lib = None  # MUST be filled in by subclass
    _defs = None
    _prefix = ''
    _err_wrap = None
    _struct_maker = None  # ffi.new
    _buflen = 512

    def __new__(cls):
        raise Exception("Not allowed to instantiate {}".format(cls))


def check_units(*pos, **named):
    """Decorator to enforce the dimensionality of input args and return values
    """
    def inout_map(arg, unit_info, name=None):
        if unit_info is None:
            return arg

        optional, units = unit_info
        if optional and arg is None:
            return None
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
    """Decorator to extract the magnitudes of input args and return values
    """
    def in_map(arg, unit_info, name):
        if unit_info is None:
            return arg

        optional, units = unit_info
        if optional and arg is None:
            return None
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
        for d, u, n in zip(defaults, pos_units[-ndefs:], arg_names[-ndefs:]):
            new_defaults[n] = d if u is None else in_map(d, u, n)

        def wrapper(*args, **kwargs):
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
        update_wrapper(wrapper, func)
        return wrapper
    return wrap
