# -*- coding: utf-8 -*-
# Copyright 2013-2019 Nate Bogdanowicz

from __future__ import division
from past.builtins import basestring
from future.utils import with_metaclass

import os
import re
import abc
import atexit
import socket
import inspect
import warnings
import contextlib
import os.path
import pickle
from weakref import WeakSet
from inspect import isfunction
from importlib import import_module

from .facet import Facet, ManualFacet, MessageFacet, SCPI_Facet, FacetGroup
from ..log import get_logger
from .. import conf
from ..util import cached_property
from ..driver_info import driver_info
from ..errors import (InstrumentTypeError, InstrumentNotFoundError, ConfigError,
                      InstrumentExistsError)

log = get_logger(__name__)


__all__ = ['Instrument', 'instrument', 'list_instruments', 'list_visa_instruments']

internal_drivers = list(driver_info.keys())  # Hacky list for back-compat usage
cleanup_funcs = []
_legacy_params = {
    'ueye_cam_id': 'uc480_camera_id',
    'pixelfly_board_num': 'pixelfly_camera_number',
    'nidaq_devname': 'ni_daq_name',
    'ccs_usb_address': 'ccs_spectrometer_usb',
    'ccs_serial_number': 'ccs_spectrometer_serial',
    'ff_serial': 'flipper_motion_serial',
}


def driver_submodule_name(full_module_name):
    return full_module_name.rsplit('instrumental.drivers.', 1)[-1]


def deprecated(name):
    """Deprecation decorator that warns on a function's first invokation"""
    def wrap(func):
        warned = []
        def wrapper(*args, **kwds):
            if not warned:
                warned.append(True)
                old_name = func.__name__
                msg = ("'{}' is deprecated and will be removed in future versions of "
                       "Instrumental. Please use '{}' instead.".format(old_name, name))
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwds)
        return wrapper
    return wrap


class ParamSet(object):
    def __init__(self, cls=None, **params):
        self._dict = params

        if cls:
            submodule_name = driver_submodule_name(cls.__module__)
            self._dict['module'] = submodule_name
            self._dict['classname'] = cls.__name__

    def __repr__(self):
        param_str = ' '.join('{}={!r}'.format(k, v) for k,v in self._dict.items()
                             if k not in ('module', 'classname'))
        if 'classname' in self._dict:
            return "<ParamSet[{}] {}>".format(self._dict['classname'], param_str)
        else:
            return "<ParamSet {}>".format(param_str)

    def create(self, **settings):
        if settings:
            if 'settings' not in self._dict:
                self._dict['settings'] = {}
            self._dict['settings'].update(settings)
        return instrument(self)

    def matches(self, other):
        """True iff all common keys have matching values"""
        return all(other[k] == v for k, v in self.items() if k in other.keys())

    def items(self):
        return self._dict.items()

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def __getitem__(self, key):
        return self._dict[key]

    def __delitem__(self, key):
        del self._dict[key]

    def __contains__(self, item):
        return item in self._dict

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def __setitem__(self, key, value):
        self._dict[key] = value

    def update(self, other):
        self._dict.update(other)

    def lazyupdate(self, other):
        """Add values from `other` for keys that are missing"""
        for key, value in other.items():
            if key not in self._dict.keys():
                self._dict[key] = value

    def to_ini(self, name):
        return '{} = {}'.format(name, self._dict)


class InstrumentMeta(abc.ABCMeta):
    """Instrument metaclass.

    Implements inheritance of method and property docstrings for subclasses of Instrument. That way
    e.g. you don't have to repeat the docstring of an abstract method, though you can provide a
    docstring in case more specific documentation is useful.

    If the child's docstring contains only a single-line function signature, it is prepended to its
    parent's docstring rather than overriding it completely. This is useful for the explicitly
    specifying signatures for methods that are wrapped by a decorator.
    """
    def __new__(metacls, clsname, bases, classdict):
        props = []
        prop_funcs = {}
        for name, value in classdict.items():
            if isinstance(value, Facet):
                value.name = name
                props.append(value)
                #if hasattr(value, 'fget'):
                #    classdict['get_' + name] = value.fget
                #if hasattr(value, 'fset'):
                #    classdict['set_' + name] = value.fset

            # Docstring stuff
            if not name.startswith('_') and (isfunction(value) or isinstance(value, property)):
                cur_doc = value.__doc__
                if cur_doc is None or (cur_doc.startswith(name) and '\n' not in cur_doc):
                    prefix = '' if cur_doc is None else cur_doc + '\n\n'
                    for base in bases:
                        if hasattr(base, name):
                            base_doc = getattr(base, name).__doc__ or ''
                            doc = prefix + base_doc

                            if isinstance(value, property):
                                # Hack b/c __doc__ is readonly for a property...
                                classdict[name] = property(value.fget, value.fset, value.fdel, doc)
                            else:
                                value.__doc__ = doc
                            break

        add_driver_info(clsname, classdict)

        classdict['_instances'] = WeakSet()
        if '__init__' in classdict:
            raise TypeError("Subclasses of Instrument may not reimplement __init__. You should "
                            "implement _initialize instead.")

        classdict['_props'] = props
        classdict['_prop_funcs'] = prop_funcs
        return super(InstrumentMeta, metacls).__new__(metacls, clsname, bases, classdict)


def add_driver_info(classname, classdict):
    """Add an entry in driver_info for class given by classname and classdict"""
    module_name = classdict['__module__']
    if module_name.startswith('instrumental.'):
        return  # Ignore internal drivers, use static driver_info
    entry = driver_info.setdefault(module_name, {})

    cls_params = classdict.get('_INST_PARAMS_', [])
    params = entry.setdefault('params', [])
    for cls_param in cls_params:
        if cls_param not in params:
            params.append(cls_param)  # Should we do this?

    entry.setdefault('classes', []).append(classname)
    entry.setdefault('imports', [])

    if 'visa_address' in cls_params:
        visa_info = entry.setdefault('visa_info', {})
        visa_info['classname'] = classdict.get('_INST_VISA_INFO_')


def driver_takes_param(module_name, param_name):
    return param_name in driver_info.get(module_name, {}).get('params', ())


class Instrument(with_metaclass(InstrumentMeta, object)):
    """
    Base class for all instruments.
    """
    _all_instances = {}

    @classmethod
    def _create(cls, paramset, **other_attrs):
        """Factory method meant to be used by `instrument()`"""
        obj = object.__new__(cls)  # Avoid our version of __new__
        for name, value in other_attrs.items():
            setattr(obj, name, value)
        obj._paramset = ParamSet(cls, **paramset)

        matching_insts = [open_inst for open_inst in obj._instances
                          if obj._paramset.matches(open_inst._paramset)]
        if matching_insts:
            if _REOPEN_POLICY == 'strict':
                raise InstrumentExistsError("Device instance already exists, cannot open in strict "
                                            "mode")
            elif _REOPEN_POLICY == 'reuse':
                # TODO: Should we return something other than the first element?
                return matching_insts[0]
            elif _REOPEN_POLICY == 'new':
                pass  # Cross our fingers and try to open a new instance

        obj._before_init()
        obj._fill_out_paramset()
        obj._initialize(**paramset.get('settings', {}))
        obj._after_init()
        return obj

    def __new__(cls, inst=None, **kwds):
        # TODO: Is there a more efficient way to implement this behavior?
        kwds['module'] = driver_submodule_name(cls.__module__)
        kwds['classname'] = cls.__name__
        return instrument(inst, **kwds)

    def _initialize(self, **settings):
        pass

    def _before_init(self):
        """Called just before _initialize"""
        self._driver_name = driver_submodule_name(self.__class__.__module__)
        # TODO: consider setting the _module at the class level
        if not hasattr(self.__class__, '_module'):
            self.__class__._module = import_driver(self._driver_name)

        facet_data = [facet.instance(self) for facet in self._props]
        self.facets = FacetGroup(facet_data)

    def _after_init(self):
        """Called just after _initialize"""
        cls = self.__class__

        # Only add the instrument after init, to ensure it hasn't failed to open
        Instrument._all_instances.setdefault(self._driver_name, {}).setdefault(cls, WeakSet()).add(self)
        self._instances.add(self)

    def _fill_out_paramset(self):
        # TODO: Fix the _INST_ system more fundamentally and remove this hack
        if hasattr(self, '_INST_PARAMS_'):
            mod_params = self._INST_PARAMS_
        else:
            try:
                mod_params = driver_info[self._driver_name]['params']
            except KeyError:
                log.info('Instrument class is lacking static info, checking module directly...')
                mod = import_module(self.__module__)
                if hasattr(mod, '_INST_PARAMS'):
                    mod_params = mod._INST_PARAMS
                elif isinstance(self, VisaMixin):
                    # Visa mixins *should* just need a visa resource
                    mod_params = ['visa_address']
                else:
                    raise
        for mod_param_name in mod_params:
            if mod_param_name not in self._paramset.keys():
                break
        else:
            log.info("Paramset has all params listed in its driver module, not filling it out")
            return

        if hasattr(self._module, 'list_instruments'):
            log.info("Filling out paramset using `list_instruments()`")
            for paramset in self._module.list_instruments():
                log.debug("Checking against %r", paramset)
                if self._paramset.matches(paramset):
                    self._paramset.lazyupdate(paramset)
                    log.info("Found match; new params: %r", self._paramset)
                    break
        else:
            log.info("Driver module missing `list_instruments()`, not filling out paramset")

    def get(self, facet_name, use_cache=False):
        facet = getattr(self.__class__, facet_name)
        if not isinstance(facet, Facet):
            raise ValueError("'{}' is not a Facet".format(facet_name))
        return facet.get_value(self, use_cache=use_cache)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        pass

    def save_instrument(self, name, force=False):
        """ Save an entry for this instrument in the config file.

        Parameters
        ----------
        name : str
            The name to give the instrument, e.g. 'myCam'
        force : bool, optional
            Force overwrite of the old entry for instrument `name`. By default,
            Instrumental will raise an exception if you try to write to a name
            that's already taken. If `force` is True, the old entry will be
            commented out (with a warning given) and a new entry will be written.
        """
        from datetime import datetime
        import os
        import os.path
        conf.load_config_file()  # Reload latest version

        if name in conf.instruments.keys():
            if not force:
                raise Exception("An entry already exists for '{}'!".format(name))
            else:
                import warnings
                warnings.warn("Commenting out existing entry for '{}'".format(name))

        try:
            paramset = self._paramset
        except AttributeError:
            raise NotImplementedError("Class '{}' does not yet support saving".format(type(self)))

        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_entry = '\n# Entry auto-created ' + date_str + '\n' + paramset.to_ini(name) + '\n'
        old_fname = os.path.join(conf.user_conf_dir, 'instrumental.conf')
        new_fname = os.path.join(conf.user_conf_dir, 'instrumental_new.conf')
        bak_fname = os.path.join(conf.user_conf_dir, 'instrumental.conf.bak')

        with open(old_fname, 'r') as old, open(new_fname, 'w') as new:
            in_section = False
            num_trailing = 0
            lines = None
            for line in old:
                if in_section:
                    if re.split(':|=', line)[0].strip() == name:
                        # Comment out existing version of this entry
                        line = '# [{} Auto-commented duplicate] '.format(date_str) + line

                    if line.startswith('['):
                        # We found the start of the *next* section
                        in_section = False
                        for l in lines[:len(lines)-num_trailing]:
                            new.write(l)

                        new.write(new_entry)

                        # Write original trailing space and new section header
                        for l in lines[len(lines)-num_trailing:]:
                            new.write(l)
                        new.write(line)
                    else:
                        lines.append(line)
                        if not line.strip():
                            num_trailing += 1
                        else:
                            num_trailing = 0
                else:
                    new.write(line)

                if line.startswith('[instruments]'):
                    in_section = True
                    lines = []

            if in_section:
                # File ended before we saw a new section
                for l in lines[:len(lines)-num_trailing]:
                    new.write(l)

                new.write(new_entry)

                # Write original trailing space
                for l in lines[len(lines)-num_trailing:]:
                    new.write(l)

        if os.path.exists(bak_fname):
            os.remove(bak_fname)
        os.rename(old_fname, bak_fname)
        os.rename(new_fname, old_fname)

        # Reload newly modified file
        conf.load_config_file()

    @cached_property
    def _state_path(self):
        if not getattr(self, '_alias', None):
            raise RuntimeError('Instrument must have an alias to provide a default path for saving '
                               'or loading its state. An alias will be set by using '
                               'save_instrument() or loading an instrument by alias')
        inst_module = inspect.getmodule(self.__class__)
        filename = '{}-{}.{}.pkl'.format(self._alias, inst_module.__name__, self.__class__.__name__)
        if not os.path.exists(conf.save_dir):
            os.makedirs(conf.save_dir)
        return os.path.join(conf.save_dir, filename)

    def _save_state(self, state_path=None):
        """Save instrument state to a pickle file"""
        state_path = state_path or self._state_path
        with open(state_path, 'wb') as f:
            pickle.dump(self.__dict__, f)

    def _load_state(self, state_path=None):
        """Load instrument state from a pickle file"""
        state_path = state_path or self._state_path
        with open(state_path, 'rb') as f:
            state = pickle.load(f)
            self.__dict__.update(state)
            print(state)

    def observe(self, name, callback):
        """Add a callback to observe changes in a facet's value

        The callback should be a callable accepting a ``ChangeEvent`` as its only argument. This
        ``ChangeEvent`` is a namedtuple with ``name``, ``old``, and ``new`` fields. ``name`` is the
        facet's name, ``old`` is the old value, and ``new`` is the new value.
        """
        facet = getattr(self.__class__, name)
        facet_instance = facet.instance(self)
        facet_instance.observe(callback)


class VisaMixin(Instrument):
    def write(self, message, *args, **kwds):
        """Write a string message to the instrument's VISA resource

        Calls format(*args, **kwds) to format the message. This allows for clean inclusion of
        parameters. For example:

        >>> inst.write('source{}:value {}', channel, value)
        """
        full_message = message.format(*args, **kwds)
        if self._in_transaction:
            if full_message[0] != ':':
                full_message = ':' + full_message
            self._message_queue.append(full_message)
        else:
            self._rsrc.write(full_message)

    def query(self, message, *args, **kwds):
        """Query the instrument's VISA resource with `message`

        Flushes the message queue if called within a transaction.
        """
        if self._in_transaction:
            self._flush_message_queue()  # TODO: combine query with this message?
        return self._rsrc.query(message.format(*args, **kwds))

    @contextlib.contextmanager
    def transaction(self):
        """Transaction context manager to auto-chain VISA messages

        Queues individual messages written with the `write()` method and sends them all at once,
        joined by ';'. Messages are actually sent (1) when a call to `query()` is made and (2)
        upon the end of transaction.

        This is especially useful when using higher-level functions that call `write()`, as it lets
        you combine multiple logical operations into a single message (if only using writes), which
        can be faster than sending lots of little messages.

        Be cognizant that a visa resource's write and query methods are not transaction-aware, only
        VisaMixin's are. If you need to call one of these methods (e.g. write_raw), make sure you
        flush the message queue manually with `_flush_message_queue()`.

        As an example:

            >>> with myinst.transaction():
            ...     myinst.write('A')
            ...     myinst.write('B')
            ...     myinst.query('C?')  # Query forces flush. Writes "A;B" and queries "C?"
            ...     myinst.write('D')
            ...     myinst.write('E')  # End of transaction block, writes "D;E"
        """
        self._start_transaction()
        yield
        self._end_transaction()

    def _start_transaction(self):
        self._message_queue = []

    def _end_transaction(self):
        self._flush_message_queue()
        self._message_queue = None  # signals end of transaction

    def _flush_message_queue(self):
        """Write all queued messages at once"""
        if not self._in_transaction:
            return
        message = ';'.join(self._message_queue)
        self._rsrc.write(message)
        self._message_queue = []

    @property
    def _in_transaction(self):
        return getattr(self, '_message_queue', None) is not None

    @property
    def resource(self):
        """VISA resource"""
        return self._rsrc


def open_visa_inst(visa_address, raise_errors=False):
    """Try to open a visa instrument.

    Logs well-known errors, and also suppress them if raise_errors is False.
    """
    import visa
    rm = visa.ResourceManager()
    try:
        log.info("Opening VISA resource '{}'".format(visa_address))
        visa_inst = rm.open_resource(visa_address, open_timeout=50, timeout=200)
    except visa.VisaIOError as e:
        # Could not create visa instrument object
        log.info("Skipping this resource due to VisaIOError")
        log.info(e)
        if raise_errors:
            raise
        else:
            return None
    except socket.timeout:
        log.info("Skipping this resource due to socket.timeout")
        if raise_errors:
            raise
        else:
            return None

    return visa_inst


def gen_visa_instruments():
    import visa
    prev_addr = 'START'
    rm = visa.ResourceManager()
    visa_list = rm.list_resources()
    for addr in visa_list:
        if addr.startswith(prev_addr):
            continue

        prev_addr = addr
        visa_inst = open_visa_inst(addr, raise_errors=False)
        if visa_inst is None:
            continue

        try:
            driver_module, classname = find_visa_driver_class(visa_inst)
            cls = getattr(driver_module, classname)
        except Exception as e:
            log.info('Exception occurred when getting correct visa driver module:')
            log.info(str(e))
            continue
        else:
            params = ParamSet(cls, visa_address=addr)
            yield params
            try_close_visa_resource(cls, visa_inst)

        finally:
            visa_inst.close()


def try_close_visa_resource(inst_class, resource):
    if not hasattr(inst_class, '_close_resource'):
        return

    try:
        log.debug('Calling %s._close_resource...', inst_class.__name__)
        inst_class._close_resource(resource)
    except Exception as e:
        log.info('Exception occurred when closing visa resource:')
        log.info(e)


def list_visa_instruments():
    """Returns a list of info about available VISA instruments.

    May take a few seconds because it must poll the network.

    It actually returns a list of specialized dict objects that contain
    parameters needed to create an instance of the given instrument. You can
    then get the actual instrument by passing the dict to
    :py:func:`~instrumental.drivers.instrument`.

    >>> inst_list = get_visa_instruments()
    >>> print(inst_list)
    [<TEKTRONIX 'TDS 3032'>, <TEKTRONIX 'AFG3021B'>]
    >>> inst = instrument(inst_list[0])
    """
    return list(gen_visa_instruments())


def list_instruments(server=None, module=None, blacklist=None):
    """Returns a list of info about available instruments.

    May take a few seconds because it must poll hardware devices.

    It actually returns a list of specialized dict objects that contain
    parameters needed to create an instance of the given instrument. You can
    then get the actual instrument by passing the dict to
    :py:func:`~instrumental.drivers.instrument`.

    >>> inst_list = get_instruments()
    >>> print(inst_list)
    [<NIDAQ 'Dev1'>, <TEKTRONIX 'TDS 3032'>, <TEKTRONIX 'AFG3021B'>]
    >>> inst = instrument(inst_list[0])

    Parameters
    ----------
    server : str, optional
        The remote Instrumental server to query. It can be an alias from your instrumental.conf
        file, or a str of the form `(hostname|ip-address)[:port]`, e.g. '192.168.1.10:12345'. Is
        None by default, meaning search on the local machine.
    blacklist : list or str, optional
        A str or list of strs indicating driver modules which should not be queried for instruments.
        Strings should be in the format ``'subpackage.module'``, e.g. ``'cameras.pco'``. This is
        useful for very slow-loading drivers whose instruments no longer need to be listed (but may
        still be in use otherwise). This can be set permanently in your ``instrumental.conf``.
    module : str, optional
        A str to filter what driver modules are checked. A driver module gets checked only if it
        contains the substring ``module`` in its full name. The full name includes both the driver
        group and the module, e.g. ``'cameras.pco'``.
    """
    if server is not None:
        from . import remote
        session = remote.client_session(server)
        return session.list_instruments()

    if blacklist is None:
        blacklist = conf.prefs['driver_blacklist']
    elif isinstance(blacklist, basestring):
        blacklist = [blacklist]

    if module:
        check_visa = any(module in driver_name and driver_name not in blacklist and
                         'visa_info' in info_dict
                         for driver_name,info_dict in driver_info.items())
    else:
        check_visa = True

    inst_list = []
    if check_visa:
        try:
            import visa
            try:
                inst_list.extend(list_visa_instruments())
            except visa.VisaIOError:
                pass  # Hide visa errors
        except (ImportError, ConfigError):
            pass  # Ignore if PyVISA not installed or configured

    if module:
        inst_list = [p for p in inst_list if module in p['module']]

    for mod_name in driver_info:
        if module and module not in mod_name:
            continue

        if mod_name in blacklist:
            log.info("Skipping blacklisted driver module '%s'", mod_name)
            continue

        driver_module = import_driver(mod_name, raise_errors=False)
        if driver_module is None:
            continue

        try:
            inst_list.extend(driver_module.list_instruments())
        except AttributeError:
            continue  # Module doesn't have a list_instruments() function
    return inst_list


def list_saved_instruments():
    return {k: ParamSet(**v) for k,v in conf.instruments.items()}


def _get_visa_instrument(params):
    """
    Returns the VISA instrument corresponding to 'visa_address'. Uses caching
    to avoid multiple network accesses.
    """
    import visa

    if 'visa_address' not in params:
        raise InstrumentTypeError()
    addr = params['visa_address']
    visa_attrs = ('baud_rate', 'timeout', 'read_termination', 'write_termination', 'parity')
    kwds = {k: v for k, v in params.items() if k in visa_attrs}

    # Check cache to see if we've already found (or not found) the instrument
    if '**visa_instrument' in params:
        visa_inst = params['**visa_instrument']
        if visa_inst is None:
            raise InstrumentNotFoundError("Error: device with address '" +
                                          addr + "' not found!")
    else:
        try:
            rm = visa.ResourceManager()
            visa_inst = rm.open_resource(addr, open_timeout=50, **kwds)
            # Cache the instrument for possible later use
            params['**visa_instrument'] = visa_inst
        except visa.VisaIOError:
            # Cache the fact that the instrument isn't connected
            params['**visa_instrument'] = None
            raise InstrumentNotFoundError("Error: device with address '" +
                                          addr + "' not found!")
        except Exception:
            params['**visa_instrument'] = None
            raise InstrumentNotFoundError("Could not connect to VISA server")

    return visa_inst


def _extract_params(inst, kwargs):
    # Look for params in a bunch of ways
    alias = None
    if inst is None:
        raw_params = {}
    elif isinstance(inst, ParamSet):
        raw_params = inst._dict
    elif isinstance(inst, dict):
        raw_params = inst
    elif isinstance(inst, basestring):
        name = inst
        raw_params = conf.instruments.get(name, None)
        if raw_params is None:
            # Try looking for the string in the output of list_instruments()
            test_str = name.lower()
            for inst_params in list_instruments():
                if test_str in str(inst_params).lower():
                    raw_params = inst_params
                    break
        else:
            alias = name

        if raw_params is None:
            raise Exception("Instrument with alias `{}` not ".format(name) +
                            "found in config file")

    params = ParamSet(**raw_params)  # Copy first to avoid modifying input dicts
    params.update(kwargs)
    return params, alias


def _init_instrument(new_inst, params):
    # HACK to allow 'parent' modules to do special initialization of instruments
    # We may get rid of this in the future by having each class's __init__ method directly
    # handle params, getting rid of the _instrument() middleman.
    parent_mod = import_module('.' + params['module'].rsplit('.', 1)[0], __package__)
    try:
        parent_mod._init_instrument(new_inst, params)
    except AttributeError:
        pass


def get_idn(inst):
    """Get manufacturer/model strings from ``*IDN?``

    Returns (None, None) if unsuccessful.
    """
    import visa
    try:
        idn = inst.query("*IDN?")
        log.info("*IDN? gives '{}'".format(idn.strip()))
    except UnicodeDecodeError as e:
        log.info("UnicodeDecodeError while getting IDN. Probably a non-Visa Serial device")
        log.info(str(e))
        return None, None
    except visa.VisaIOError as e:
        log.info("Getting IDN failed due to VisaIOError")
        log.info(str(e))
        return None, None
    except socket.timeout:
        log.info("Getting IDN failed due to socket.timeout")
        return None, None

    try:
        manufac, model, _ = idn.split(',', 2)
        manufac = manufac.strip()
        model = model.strip()
    except ValueError as e:
        log.info("Invalid response to IDN query")
        log.info(str(e))
        return None, None

    return manufac, model


def import_driver(driver_name, raise_errors=False):
    try:
        log.info("Importing driver module '%s'", driver_name)
        # TODO: store full module names in driver_info (or add leading dot) so that external
        # drivers don't have possible name conflicts
        if driver_name in internal_drivers:
            return import_module('.' + driver_name, __package__)
        else:
            return import_module(driver_name)
    except Exception as e:
        log.info("Error when importing driver module %s: <<%s>>", driver_name, str(e))
        if raise_errors:
            raise
        else:
            return None


def find_matching_drivers(in_params):
    """Find all drivers to which `in_params` could refer

    This is for matching non-VISA parameter sets with all the drivers that may support them.
    """
    matching_drivers = []
    split_params = []
    for in_param, value in in_params.items():
        in_param = _legacy_params.get(in_param, in_param)
        tup = in_param.split('_', 2)
        split_params.append((tup[:-1], tup[-1], value))

    for driver_fullname, info in driver_info.items():
        driver_group, driver_module = driver_fullname.split('.')
        driver_params = info['params']
        normalized_params = {}
        log.debug("Checking against %r", (driver_fullname, driver_params))
        for filters, base_param, value in split_params:
            log.debug("Param filters: %r", filters)
            log.debug("Base param: %r", base_param)

            for driver_param in driver_params:
                if base_param in driver_param:
                    matching_param = driver_param
                    break
            else:
                break

            if len(filters) == 2:
                # Both must match
                mod_name, category = filters
                if mod_name not in driver_module or category not in driver_group:
                    break
            elif len(filters) == 1:
                # Filter must match one
                filt, = filters
                if filt not in driver_module and filt not in driver_group:
                    break

            normalized_params[matching_param] = value
        else:
            # All given params match this driver
            matching_drivers.append((driver_fullname, normalized_params))
    return matching_drivers


def find_visa_instrument(params):
    import visa
    rm = visa.ResourceManager()
    visa_address = params['visa_address']

    if 'module' in params:
        driver_module = import_driver(params['module'], raise_errors=True)
        if hasattr(driver_module, '_instrument'):
            return driver_module._instrument(params)

        log.info("Opening VISA resource '{}'".format(visa_address))
        visa_inst = rm.open_resource(visa_address, open_timeout=50, timeout=200)

        if 'classname' in params:
            classname = params['classname']
        else:
            try:
                _, classname = find_visa_driver_class(visa_inst, params['module'])
            except Exception as e:
                visa_inst.close()
                log.exception(e)
                raise Exception("Couldn't find class in the given module that supports this "
                                "VISA instrument")

        return create_instrument(driver_module, classname, params, visa_inst)

    else:
        log.info("Opening VISA resource '{}'".format(visa_address))
        visa_inst = rm.open_resource(visa_address, open_timeout=50, timeout=200)

        try:
            driver_module, classname = find_visa_driver_class(visa_inst)
        except Exception:
            visa_inst.close()
            raise

        if hasattr(driver_module, '_instrument'):
            return driver_module._instrument(params)
        else:
            return create_instrument(driver_module, classname, params, visa_inst)


def create_instrument(driver_module, classname, paramset, visa_inst=None):
    log.info("Creating instrument using default method")
    cls = getattr(driver_module, classname)
    if visa_inst is not None:
        return cls._create(paramset, _rsrc=visa_inst)
    else:
        return cls._create(paramset)


def find_visa_instrument_by_module(in_paramset):
    driver_name = in_paramset['module']
    # This may be slower than strictly necessary, since it tries all visa addresses in order,
    # instead of filtering based on address type. That would require extra machinery though
    for test_paramset in gen_visa_instruments():
        if test_paramset['module'] == driver_name:
            in_paramset.lazyupdate(test_paramset)
            return in_paramset.create()
    raise Exception("No instrument from driver {} detected".format(driver_name))


def find_visa_driver_class(visa_inst, module=None):
    """Search for the appropriate VISA driver, returning (driver_module, classname)

    First checks based on the manufacturer/model returned by ``*IDN?``, then ``_check_visa_support``
    until a match is found. Raises an exception if no match is found.
    """
    if module:
        all_info = [(drv_name, mod_info['visa_info'])
                    for (drv_name, mod_info) in driver_info.items()
                    if 'visa_info' in mod_info and drv_name == module]
    else:
        all_info = [(drv_name, mod_info['visa_info'])
                    for (drv_name, mod_info) in driver_info.items()
                    if 'visa_info' in mod_info]

    module_supports_idn = any(info for _,info in all_info)
    if module_supports_idn:
        log.info('Checking IDN...')
        inst_manufac, inst_model = get_idn(visa_inst)

        # Match IDN against driver manufac/model
        if inst_manufac:
            for driver_fullname, visa_info in all_info:
                log.info("Checking manufac/model against those in %s", driver_fullname)
                for classname, (cls_manufac, cls_models) in visa_info.items():
                    if inst_manufac == cls_manufac and inst_model in cls_models:
                        log.info("Match found: %s, %s", driver_fullname, classname)
                        driver_module = import_driver(driver_fullname, raise_errors=True)
                        return driver_module, classname

    # Manually try visa-based drivers
    log.info('Checking support via `_check_visa_support()`...')
    for driver_fullname, _ in all_info:
        driver_module = import_driver(driver_fullname, raise_errors=False)
        if driver_module is None:
            continue

        if not hasattr(driver_module, '_check_visa_support'):
            log.info("Module %s missing _check_visa_support(), skipping", driver_fullname)
            continue

        log.info("Checking if '%s' has a matching class", driver_fullname)
        classname = driver_module._check_visa_support(visa_inst)

        if classname:
            return driver_module, classname

    raise Exception("No matching VISA driver found")


def find_nonvisa_instrument(params):
    if 'module' in params:
        driver_module = import_driver(params['module'], raise_errors=True)
        normalized_params = {_legacy_params.get(k, k).rsplit('_', 1)[-1]:v
                             for k,v in params.items()}
        if hasattr(driver_module, '_instrument'):
            return driver_module._instrument(normalized_params)

        full_params = find_full_params(normalized_params, driver_module)
        if not full_params:
            # FIXME: Improve this error message
            raise Exception("{} does not match any known ParamSet from driver module "
                            "{}.".format(params, params['module']))

        classnames = driver_info[params['module']]['classes']
        for classname in classnames:
            try:
                return create_instrument(driver_module, classname, normalized_params)
            except (InstrumentTypeError, InstrumentNotFoundError):
                log.info("Failed to create instrument using '%s'", classname)

        raise Exception("Could not open non-VISA instrument. Driver module '{}' is missing "
                        "_instrument function, and the listed instrument classes {} "
                        "Failed to handle these params.".format(params['module'], classnames))
    else:
        ok_drivers = find_matching_drivers(params)
        if not ok_drivers:
            raise Exception("Parameters {} match no existing driver module".format(params))

        raise_errors = (len(ok_drivers) == 1)
        for driver_name, normalized_params in ok_drivers:
            driver_module = import_driver(driver_name, raise_errors=raise_errors)
            if driver_module is None:
                continue

            if hasattr(driver_module, '_instrument'):
                inst = call_instrument_func(driver_module, normalized_params,
                                            raise_errors=(len(ok_drivers) == 1))
                if not inst:
                    continue
            else:
                full_params = find_full_params(normalized_params, driver_module)
                if not full_params:
                    log.info("%s does not match any known ParamSet from driver module %s",
                             params, driver_name)
                    continue

                classnames = driver_info[driver_name]['classes']
                for classname in classnames:
                    try:
                        return create_instrument(driver_module, classname, normalized_params)
                    except Exception as e:
                        log.info("Failed to create instrument using '%s'", classname)
                        log.info(str(e))
                        if len(ok_drivers) == len(classnames) == 1:
                            raise
                log.info("All classes given in this module failed to create instrument")
                continue

            normalized_params['module'] = driver_name
            _init_instrument(inst, normalized_params)
            return inst


def call_instrument_func(driver_module, normalized_params, raise_errors):
    try:
        log.info("Trying to create instrument using module '%s'", driver_module.__name__)
        return driver_module._instrument(normalized_params)
    except AttributeError:
        if raise_errors: raise
        log.info("Module missing _instrument()")
    except InstrumentTypeError:
        if raise_errors: raise
        log.info("Not the right type")
    except InstrumentNotFoundError:
        if raise_errors: raise
        log.info("Instrument not found")

    return None


def find_full_params(normalized_params, driver_module):
    log.info('Filling out full params')
    if not hasattr(driver_module, 'list_instruments'):
        log.info("Driver module missing `list_instruments()`, not filling out paramset")
        return normalized_params

    for inst_params in driver_module.list_instruments():
        if inst_params.matches(normalized_params):
            return inst_params


# Pretty hacky, but is actually the *least* crazy way I can think of doing this right now. Somehow
# we have to get this info to the Instrument class when it's instantiating a new instrument, the
# paths to that code are many, varied, and winding.
_REOPEN_POLICY = None
@contextlib.contextmanager
def _reopen_context(reopen_policy):
    global _REOPEN_POLICY
    if reopen_policy not in ('strict', 'reuse', 'new'):
        raise ValueError("Reopen policy must be one of 'strict', 'reuse', 'new'")
    _REOPEN_POLICY = reopen_policy
    yield
    _REOPEN_POLICY = None


def instrument(inst=None, **kwargs):
    """
    Create any Instrumental instrument object from an alias, parameters,
    or an existing instrument.

    reopen_policy : str of ('strict', 'reuse', 'new'), optional
        How to handle the reopening of an existing instrument.
        'strict' - disallow reopening an instrument with an existing instance which hasn't been
        cleaned up yet.
        'reuse' - if an instrument is being reopened, return the existing instance
        'new' - always create a new instance of the instrument class. *Not recommended* unless you
        know exactly what you're doing. The instrument objects are not synchronized with one
        another.
        By default, follows the 'reuse' policy.

    >>> inst1 = instrument('MYAFG')
    >>> inst2 = instrument(visa_address='TCPIP::192.168.1.34::INSTR')
    >>> inst3 = instrument({'visa_address': 'TCPIP:192.168.1.35::INSTR'})
    >>> inst4 = instrument(inst1)
    """
    log.info('Called instrument() with inst=%s, kwargs=%s', inst, kwargs)
    if isinstance(inst, Instrument):
        return inst

    with _reopen_context(kwargs.pop('reopen_policy', 'reuse')):
        params, alias = _extract_params(inst, kwargs)

        if 'server' in params:
            from . import remote
            host = params['server']
            session = remote.client_session(host)
            inst = session.instrument(params)
        elif 'visa_address' in params:
            inst = find_visa_instrument(params)
        elif 'module' in params and driver_takes_param(params['module'], 'visa_address'):
            inst = find_visa_instrument_by_module(params)
        else:
            inst = find_nonvisa_instrument(params)

        if inst is None:
            raise Exception("No instrument found that matches {}".format(params))

        inst._alias = alias
        return inst


def register_cleanup(func):
    """Register a cleanup function to be called after Instrument cleanup.

    This is for module and class-level cleanup (e.g. for closing a library), to ensure it is called
    *after* all Instruments are cleaned up. Can be used as a decorator.
    """
    cleanup_funcs.append(func)
    return func


@atexit.register
def _close_atexit():
    log.info('Program is exiting, closing all instruments...')
    for class_instances in Instrument._all_instances.values():
        for instances in class_instances.values():
            for inst in instances:
                log.info('Closing %s', inst)
                try:
                    inst.close()
                except Exception:
                    pass  # Instrument may have already been closed
    log.info('Done closing instruments')

    log.info('Doing driver module-level cleanup...')
    for cleanup_func in cleanup_funcs:
        try:
            if hasattr(cleanup_func, '__name__'):
                log.info("Calling '%s'", cleanup_func.__name__)
            else:
                log.info("Calling cleanup function")

            cleanup_func()
        except Exception as e:
            log.error(str(e))
