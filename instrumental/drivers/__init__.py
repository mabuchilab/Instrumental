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
from ..errors import InstrumentTypeError, InstrumentNotFoundError, ConfigError

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
    parent's docstring rather than overriding it comopletely. This is useful for the explicitly
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
                            doc = prefix + getattr(base, name).__doc__

                            if isinstance(value, property):
                                # Hack b/c __doc__ is readonly for a property...
                                classdict[name] = property(value.fget, value.fset, value.fdel, doc)
                            else:
                                value.__doc__ = doc
                            break
        return super(InstrumentMeta, metacls).__new__(metacls, clsname, bases, classdict)


class Instrument(object):
    """
    Base class for all instruments.
    """
    __metaclass__ = InstrumentMeta
    _instruments_to_close = []

    def _register_close_atexit(self):
        """Register this instrument to be auto-closed upon program termination

        The instrument must have a `close()` method.
        """
        Instrument._instruments_to_close.append(self)

    @classmethod
    def _close_atexit(cls):
        for inst in cls._instruments_to_close:
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


def _find_visa_inst_type(manufac, model):
    for mod_name, tup in _visa_models.items():
        mod_manufac, mod_models = tup
        if manufac == mod_manufac and model in mod_models:
            return mod_name
    return None


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
    import visa
    instruments, skipped = [], []
    prev_addr = 'START'
    rm = visa.ResourceManager()
    visa_list = rm.list_resources()
    for addr in visa_list:
        if not addr.startswith(prev_addr):
            prev_addr = addr
            try:
                log.info("Opening VISA resource '{}'".format(addr))
                i = rm.open_resource(addr, open_timeout=50, timeout=200)
            except visa.VisaIOError as e:
                # Could not create visa instrument object
                skipped.append(addr)
                log.info("Skipping this resource due to VisaIOError")
                log.info(e)
                continue
            except socket.timeout:
                skipped.append(addr)
                log.info("Skipping this resource due to socket.timeout")
                continue

            try:
                idn = i.ask("*IDN?")
                log.info("*IDN? gives '{}'".format(idn.strip()))
                try:
                    manufac, model, rest = idn.split(',', 2)
                except ValueError as e:
                    skipped.append(addr)
                    log.info("Invalid response to IDN query")
                    log.info(str(e))
                    continue

                module_name = _find_visa_inst_type(manufac, model)
                params = _ParamDict("<{} '{}'>".format(manufac, model))
                params['visa_address'] = addr
                if module_name:
                    params['module'] = module_name
                instruments.append(params)
            except UnicodeDecodeError as e:
                skipped.append(addr)
                log.info("UnicodeDecodeError while getting IDN. Probably a non-Visa Serial device")
                log.info(str(e))
                continue
            except visa.VisaIOError as e:
                skipped.append(addr)
                log.info("Getting IDN failed due to VisaIOError")
                log.info(str(e))
                continue
            except socket.timeout:
                skipped.append(addr)
                log.info("Getting IDN failed due to socket.timeout")
                continue
            finally:
                i.close()
    return instruments


def list_instruments(server=None, module=None):
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
    """
    if server is not None:
        from . import remote
        session = remote.client_session(server)
        return session.list_instruments()

    try:
        import visa
        try:
            inst_list = list_visa_instruments()
        except visa.VisaIOError:
            inst_list = []  # Hide visa errors
    except (ImportError, ConfigError):
        inst_list = []  # Ignore if PyVISA not installed or configured

    for mod_name in _acceptable_params:
        if module and module not in mod_name:
            continue

        try:
            log.info("Importing driver module '%s'", mod_name)
            mod = import_module('.' + mod_name, __package__)
        except Exception as e:
            # Module not supported
            log.info("Error when importing module %s: <<%s>>", mod_name, str(e))
            continue

        try:
            inst_list.extend(mod.list_instruments())
        except AttributeError:
            # Module doesn't have a list_instruments() function
            continue
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


def _has_acceptable_params(acceptable, given):
    """ Returns true if given contains a param in the acceptable list. """
    for p in given:
        if p in acceptable:
            return True
    return False


def instrument(inst=None, **kwargs):
    """
    Create any Instrumental instrument object from an alias, parameters,
    or an existing instrument.

    >>> inst1 = instrument('MYAFG')
    >>> inst2 = instrument(visa_address='TCPIP::192.168.1.34::INSTR')
    >>> inst3 = instrument({'visa_address': 'TCPIP:192.168.1.35::INSTR'})
    >>> inst4 = instrument(inst1)
    """
    alias = None
    if inst is None:
        params = {}
    elif isinstance(inst, Instrument):
        return inst
    elif isinstance(inst, dict):
        params = inst
    elif isinstance(inst, basestring):
        name = inst
        params = conf.instruments.get(name, None)
        if params is None:
            # Try looking for the string in the output of list_instruments()
            test_str = name.lower()
            for inst_params in list_instruments():
                if test_str in str(inst_params).lower():
                    params = inst_params
                    break
        else:
            alias = name

        if params is None:
            raise Exception("Instrument with alias `{}` not ".format(name) +
                            "found in config file")

    params = params.copy()  # Make sure we don't modify any existing dicts
    params.update(kwargs)

    if 'server' in params:
        from . import remote
        host = params['server']
        session = remote.client_session(host)
        return session.instrument(params)

    if 'module' in params:
        # We've already been given the name of the module
        # SHOULD PROBABLY INTEGRATE THIS WITH THE OTHER CASE
        try:
            mod = import_module('.' + params['module'], __package__)
        except Exception as e:
            msg = ("\n\nSpecified module '{}' could not be imported. Make sure you have all of "
                   "this driver module's dependencies installed.".format(params['module']))
            e.args = (str(e.args[0]) + msg,) + e.args[1:]
            raise

        try:
            new_inst = mod._instrument(params)
        except InstrumentTypeError:
            raise Exception("Instrument is not compatible with the given module")

        new_inst._alias = alias

        # HACK to allow 'parent' modules to do special initialization of instruments
        # We may get rid of this in the future by having each class's __init__ method directly
        # handle params, getting rid of the _instrument() middleman.
        parent_mod = import_module('.' + params['module'].rsplit('.', 1)[0], __package__)
        try:
            parent_mod._init_instrument(new_inst, params)
        except AttributeError:
            pass

        return new_inst

    # Find the right type of Instrument to create
    acceptable_modules = [mod_name for mod_name, acc_params in _acceptable_params.items()
                          if _has_acceptable_params(acc_params, params)]

    for mod_name in acceptable_modules:
        # Try to import module, skip it if optional deps aren't met
        try:
            log.info("Trying to import module '{}'".format(mod_name))
            mod = import_module('.' + mod_name, __package__)
        except Exception as e:
            if len(acceptable_modules) == 1: raise
            log.info("Module {} not supported, skipping".format(mod_name), exc_info=e)
            continue

        # Try to create an instance of this instrument type
        try:
            log.info("Trying to create instrument using module '{}'".format(mod_name))
            new_inst = mod._instrument(params)
        except AttributeError:
            if len(acceptable_modules) == 1: raise
            log.info("Module {} missing _instrument(), skipping".format(mod_name))
            continue
        except InstrumentTypeError:
            if len(acceptable_modules) == 1: raise
            log.info("Not the right type")
            continue
        except InstrumentNotFoundError:
            if len(acceptable_modules) == 1: raise
            log.info("Instrument not found")
            continue

        new_inst._alias = alias

        # HACK to allow 'parent' modules to do special initialization of instruments
        # We may get rid of this in the future by having each class's __init__ method directly
        # handle params, getting rid of the _instrument() middleman.
        parent_mod = import_module('.' + mod_name.rsplit('.', 1)[0], __package__)
        try:
            parent_mod._init_instrument(new_inst, params)
        except AttributeError:
            pass

        return new_inst

    # If we reach this point, we haven't been able to create a valid instrument
    if not acceptable_modules:
        raise Exception("Parameters {} match no existing driver module".format(params))
    else:
        raise Exception("No instrument matching {} was found".format(params))


atexit.register(Instrument._close_atexit)
