# -*- coding: utf-8 -*-
# Copyright 2013-2017 Nate Bogdanowicz

import re
import abc
import atexit
import socket
import logging as log
from inspect import isfunction
from importlib import import_module
from collections import OrderedDict

from past.builtins import basestring

from .. import conf
from ..driver_info import driver_info
from ..errors import (InstrumentTypeError, InstrumentNotFoundError, ConfigError,
                      InstrumentExistsError)


__all__ = ['Instrument', 'instrument', 'list_instruments', 'list_visa_instruments']

_legacy_params = {
    'ueye_cam_id': 'uc480_camera_id',
    'pixelfly_board_num': 'pixelfly_camera_number',
    'nidaq_devname': 'ni_daq_name',
}

# Listing of acceptable parameters for each driver module
_acceptable_params = OrderedDict((
    ('cameras.uc480',
        ['ueye_cam_id', 'cam_serial']),
    ('cameras.tsi',
        ['tsi_cam_ser', 'tsi_cam_num']),
    ('cameras.pixelfly',
        ['pixelfly_board_num', 'module']),
    ('cameras.pco',
        ['pco_cam_num', 'module']),
    ('cameras.pvcam',
        ['pvcam_name', 'module']),
    ('daq.ni',
        ['nidaq_devname']),
    ('funcgenerators.tektronix',
        ['visa_address']),
    ('scopes.tektronix',
        ['visa_address']),
    ('multimeters.hp',
        ['visa_address']),
    ('powermeters.thorlabs',
        ['visa_address']),
    ('powermeters.newport',
        ['visa_address', 'module']),
    ('wavemeters.burleigh',
        ['visa_address', 'module']),
    ('spectrometers.bristol',
        ['bristol_port', 'module']),
    ('lockins.sr850',
        ['visa_address', 'module']),
    ('motion.filter_flipper',
        ['ff_serial']),
    ('motion.tdc_001',
        ['tdc_serial']),
    ('motion.ecc100',
        ['ecc100_id', 'module']),
    ('lasers.femto_ferb',
        ['femto_ferb_port']),
    ('motion.esp300',
        ['esp300_port']),
    ('spectrometers.thorlabs_ccs',
        ['ccs_usb_address', 'ccs_serial_number', 'ccs_model', 'module']),
    ('vacuum.sentorr_mod',
        ['sentorrmod_port']),
))

_visa_models = OrderedDict((
    ('funcgenerators.tektronix', (
        'TEKTRONIX',
        ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102',
         'AFG3251', 'AFG3252']
    )),
    ('multimeters.hp', (
        'HEWLETT-PACKARD',
        ['34401A']
    )),
    ('scopes.tektronix', (
        'TEKTRONIX',
        ['TDS 3032', 'TDS 3034B', 'MSO4034', 'DPO4034']
    )),
    ('powermeters.thorlabs', (
        'Thorlabs',
        ['PM100D']
    )),
    # Note that the sr850 will not usually work with list_visa_instruments,
    # because it uses a non-standard termination character, and because one
    # must first send the 'OUTX' command to specify which type of output to use
    ('lockins.sr850', (
        'Stanford_Research_Systems',
        ['SR850']
    ))
))


class Params(object):
    def __init__(self, module_name=None, cls=None, **params):
        self._dict = params
        self._cls = cls

        if module_name:
            submodule_name = module_name.split('instrumental.drivers.', 1)[-1]
            self._dict['module'] = submodule_name
            self._dict['classname'] = self._cls.__name__

    @staticmethod
    def from_dict(data):
        obj = Params()
        obj._dict = data.copy()
        return obj

    def __repr__(self):
        param_str = ' '.join('{}={!r}'.format(k, v) for k,v in self._dict.items()
                             if k not in ('module', 'classname'))
        if self._cls:
            return "<Params[{}] {}>".format(self._cls.__name__, param_str)
        else:
            return "<Params {}>".format(param_str)

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


class _ParamDict(dict):
    def __init__(self, name):
        self.name = name
        self['module'] = None

    def __str__(self):
        if self.name:
            return self.name
        return "<_ParamDict>"

    def __repr__(self):
        return self.__str__()

    def to_ini(self, name):
        return '{} = {}'.format(name, dict(self))


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
        for name, value in classdict.items():
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

        classdict['_instances'] = []
        if '__init__' in classdict:
            original_init = classdict['__init__']

            def __init__(self, paramset, *args, **kwds):
                if self._init_nest_level == 0:
                    Instrument._before_init(self, paramset, *args, **kwds)
                paramset = self._paramset  # This should have been set by _before_init

                self._init_nest_level += 1
                original_init(self, paramset, *args, **kwds)
                self._init_nest_level -= 1

                if self._init_nest_level == 0:
                    Instrument._after_init(self, paramset, *args, **kwds)
            classdict['__init__'] = __init__
        return super(InstrumentMeta, metacls).__new__(metacls, clsname, bases, classdict)


class Instrument(object):
    """
    Base class for all instruments.
    """
    __metaclass__ = InstrumentMeta
    _instruments_to_close = []
    _all_instances = {}
    _allow_sharing = False  # Should we allow returning existing instruments?
    _init_nest_level = 0

    def _before_init(self, paramset, *args, **kwds):
        """Called just before __init__, with the same parameters"""
        cls = self.__class__
        _, _, self._driver_name = cls.__module__.rpartition('instrumental.drivers.')
        self._module = import_driver(self._driver_name)

        self._paramset = Params(cls.__module__, cls, **paramset)
        self._fill_out_paramset()

        if not self._allow_sharing:
            for open_inst in self._instances:
                if self._paramset.matches(open_inst._paramset):
                    raise InstrumentExistsError("Device already open")

    def _after_init(self, paramset, *args, **kwds):
        """Called just after __init__, with the same parameters"""
        cls = self.__class__

        # Only add the instrument after init, to ensure it hasn't failed to open
        Instrument._all_instances.setdefault(self._driver_name, {}).setdefault(cls, []).append(self)
        self._instances.append(self)

    def _fill_out_paramset(self):
        mod_params = driver_info[self._driver_name]['params']
        for mod_param_name in mod_params:
            if mod_param_name not in self._paramset.keys(): break
        else:
            log.info("Paramset has all params listed in its driver module, not filling it out")
            return

        if hasattr(self._module, 'list_instruments'):
            log.info("Filling out paramset")
            for paramset in self._module.list_instruments():
                if self._paramset.matches(paramset):
                    self._paramset.lazyupdate(paramset)
                    break
        else:
            log.info("Driver module missing `list_instruments()`, not filling out paramset")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        pass

    def _register_close_atexit(self):
        """Register this instrument to be auto-closed upon program termination

        The instrument must have a `close()` method.
        """
        Instrument._instruments_to_close.append(self)

    @staticmethod
    def _close_atexit():
        for class_instances in Instrument._all_instances.values():
            for instances in class_instances.values():
                for inst in instances:
                    try:
                        inst.close()
                    except:
                        pass  # Instrument may have already been closed

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
            pdict = self._param_dict
        except AttributeError:
            raise NotImplementedError("Class '{}' does not yet support saving".format(type(self)))

        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_entry = '\n# Entry auto-created ' + date_str + '\n' + pdict.to_ini(name) + '\n'
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
            params = Params(driver_module.__name__, cls, visa_address=addr)
        except:
            continue
        else:
            yield params
        finally:
            visa_inst.close()


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

    try:
        import visa
        try:
            inst_list = list_visa_instruments()
        except visa.VisaIOError:
            inst_list = []  # Hide visa errors
    except (ImportError, ConfigError):
        inst_list = []  # Ignore if PyVISA not installed or configured

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


def saved_instruments():
    return conf.instruments.keys()


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
    elif isinstance(inst, Instrument):
        return inst
    elif isinstance(inst, Params):
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

    params = Params.from_dict(raw_params)  # Copy first to avoid modifying input dicts
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
        idn = inst.ask("*IDN?")
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
    except ValueError as e:
        log.info("Invalid response to IDN query")
        log.info(str(e))
        return None, None

    return manufac, model


def import_driver(driver_name, raise_errors=False):
    try:
        log.info("Importing driver module '%s'", driver_name)
        return import_module('.' + driver_name, __package__)
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


# find_visa_instrument(params):
#   if module given:
#     if _instrument in module:
#       open using _instrument() and return
#     else:
#       open visa_inst
#       if classname not given:
#         try:
#           module, class = find_visa_module(visa_inst)
#         except:
#           close visa_inst
#           raise exception(Couldn't find matching instrument given this module)
#
#       open directly using class and return
#   else:
#     open visa_inst
#     try:
#       module, class = find_visa_module(visa_inst)
#     except:
#       close visa_inst
#       raise
#
#     import module
#
#     if _instrument in module:
#       open using _instrument() and return
#     else:
#       open directly using class and return
#
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
                _, classname = find_visa_driver_class(visa_inst)
            except:
                visa_inst.close()
                raise Exception("Couldn't find class in the given module that supports this "
                                "VISA instrument")

        return create_instrument(driver_module, classname, params, visa_inst)

    else:
        log.info("Opening VISA resource '{}'".format(visa_address))
        visa_inst = rm.open_resource(visa_address, open_timeout=50, timeout=200)

        try:
            driver_module, classname = find_visa_driver_class(visa_inst)
        except:
            visa_inst.close()
            raise

        if hasattr(driver_module, '_instrument'):
            return driver_module._instrument(params)
        else:
            return create_instrument(driver_module, classname, params, visa_inst)


def create_instrument(driver_module, classname, paramset, visa_inst=None):
    log.info("Creating instrument using default method")
    cls = getattr(driver_module, classname)
    settings = paramset.get('settings', {})
    if visa_inst is not None:
        return cls(paramset, visa_inst, **settings)
    else:
        return cls(paramset, **settings)


def find_visa_instrument_by_module(in_paramset):
    driver_name = in_paramset['module']
    # This may be slower than strictly necessary, since it tries all visa addresses in order,
    # instead of filtering based on address type. That would require extra machinery though
    for test_paramset in gen_visa_instruments():
        if test_paramset['module'] == driver_name:
            in_paramset.lazyupdate(test_paramset)
            return in_paramset.create()
    raise Exception("No instrument from driver {} detected".format(driver_name))


# find_visa_module(visa_inst, module=None):
#   modules = [module] if module else all-visa-drivers
#   try to get idn
#   if successful:
#     for driver in visa drivers with manufac/model:
#       return (driver, classname) if manufac/model match idn
#
#   for driver in visa drivers:
#     return (driver, classname) if _check_visa_support returns them (catch exceptions?)
#
#   raise exception("No matching visa driver found")
#
def find_visa_driver_class(visa_inst, module=None):
    """Search for the appropriate VISA driver, returning (driver_module, classname)

    First checks based on the manufacturer/model returned by ``*IDN?``, then ``_check_visa_support``
    until a match is found. Raises an exception if no match is found.
    """
    if module:
        all_info = ((drv_name, mod_info['visa_info']) for (drv_name, mod_info) in driver_info.items()
                    if 'visa_info' in mod_info and drv_name == module)
    else:
        all_info = ((drv_name, mod_info['visa_info']) for (drv_name, mod_info) in driver_info.items()
                    if 'visa_info' in mod_info)

    inst_manufac, inst_model = get_idn(visa_inst)

    # Match against driver manufac/model
    if inst_manufac:
        for driver_fullname, visa_info in all_info:
            log.info("Checking manufac/model against those in %s", driver_fullname)
            for classname, (cls_manufac, cls_models) in visa_info.items():
                if inst_manufac == cls_manufac and inst_model in cls_models:
                    log.info("Match found: %s, %s", driver_fullname, classname)
                    driver_module = import_driver(driver_fullname, raise_errors=True)
                    return driver_module, classname

    # Manually try visa-based drivers
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


# find_nonvisa_instrument(params):
#   if module given:
#     if _instrument not in module:
#       raise exception(Driver module is missing _instrument)
#     else:
#       open using _instrument()
#   else:
#     filter drivers by the given params
#     if no such drivers:
#       raise exception(No drivers found matching those params)
#
#     for each param-matching nonvisa driver module:
#       try opening using _instrument()
#       return if successful, else continue
#     else:
#       raise exception(No instrument matching these params was found)
#
def find_nonvisa_instrument(params):
    if 'module' in params:
        driver_module = import_driver(params['module'], raise_errors=True)
        normalized_params = {_legacy_params.get(k, k).rsplit('_', 1)[-1]:v for k,v in params.items()}
        if hasattr(driver_module, '_instrument'):
            return driver_module._instrument(normalized_params)

        full_params = find_full_params(normalized_params, driver_module)
        if not full_params:
            raise Exception("{} does not match any known Params from driver module "
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

        for driver_name, normalized_params in ok_drivers:
            driver_module = import_driver(driver_name, raise_errors=False)
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
                    log.info("%s does not match any known Params from driver module %s",
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


# Pseudocode:
#
# Handle input params
#
# if 'server' in params:
#   return remote instrument
# elif 'visa_address' in params:
#   return find_visa_instrument(params)
# else:
#   return find_nonvisa_instrument(params)
#
def instrument(inst=None, **kwargs):
    """
    Create any Instrumental instrument object from an alias, parameters,
    or an existing instrument.

    >>> inst1 = instrument('MYAFG')
    >>> inst2 = instrument(visa_address='TCPIP::192.168.1.34::INSTR')
    >>> inst3 = instrument({'visa_address': 'TCPIP:192.168.1.35::INSTR'})
    >>> inst4 = instrument(inst1)
    """
    params, alias = _extract_params(inst, kwargs)

    if 'server' in params:
        from . import remote
        host = params['server']
        session = remote.client_session(host)
        inst = session.instrument(params)
    elif 'visa_address' in params:
        inst = find_visa_instrument(params)
    elif 'module' in params and 'visa_address' in driver_info[params['module']]['params']:
        inst = find_visa_instrument_by_module(params)
    else:
        inst = find_nonvisa_instrument(params)

    if inst is None:
        raise Exception("No instrument found that matches {}".format(params))

    inst._alias = alias
    return inst


atexit.register(Instrument._close_atexit)
