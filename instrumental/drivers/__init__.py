# -*- coding: utf-8 -*-
# Copyright 2013-2015 Nate Bogdanowicz

import re
import socket
import logging as log
from importlib import import_module

from .. import conf
from ..errors import InstrumentTypeError, InstrumentNotFoundError, ConfigError

# Listing of acceptable parameters for each driver module
_acceptable_params = {
    'cameras.uc480':
        ['ueye_cam_id', 'cam_serial'],
    'cameras.pixelfly':
        ['pixelfly_board_num', 'module'],
    'cameras.pvcam':
        ['pvcam_name', 'module'],
    'daq.ni':
        ['nidaq_devname'],
    'funcgenerators.tektronix':
        ['visa_address'],
    'scopes.tektronix':
        ['visa_address'],
    'powermeters.newport':
        ['visa_address', 'module'],
    'powermeters.thorlabs':
        ['visa_address'],
    'wavemeters.burleigh':
        ['visa_address', 'module']
}

_visa_models = {
    'funcgenerators.tektronix': (
        'TEKTRONIX',
        ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102',
         'AFG3251', 'AFG3252']
    ),
    'scopes.tektronix': (
        'TEKTRONIX',
        ['TDS 3032', 'TDS 3034B', 'MSO4034', 'DPO4034']
    ),
    'powermeters.thorlabs': (
        'Thorlabs',
        ['PM100D']
    )
}


class _ParamDict(dict):
    def __init__(self, name):
        self.name = name
        self.module = None

    def __str__(self):
        if self.name:
            return self.name
        return "<_ParamDict>"

    def __repr__(self):
        return self.__str__()

    def to_ini(self, name):
        return '{} = {}'.format(name, dict(self))


class Instrument(object):
    """
    Base class for all instruments.
    """
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
        conf.load_config_file() # Reload latest version

        if name in conf.instruments.keys():
            if not force:
                raise Exception("An entry already exists for '{}'!".format(name))
            else:
                import warnings
                warnings.warn("Commenting out existing entry for '{}'".format(name))

        try:
            pdict = self._param_dict
        except AttributeError:
            raise NotImplementedError("Class '{}' does not yet support saving")

        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_entry = '\n# Entry auto-created ' + date_str + '\n' + pdict.to_ini(name) + '\n'
        old_fname = os.path.join(conf.data_dir, 'instrumental.conf')
        new_fname = os.path.join(conf.data_dir, 'instrumental_new.conf')
        bak_fname = os.path.join(conf.data_dir, 'instrumental.conf.bak')

        with open(old_fname, 'r') as old, open(new_fname, 'w') as new:
            in_section = False
            num_trailing = 0
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
    from .. import visa
    instruments, skipped = [], []
    prev_addr = 'START'
    rm = visa.ResourceManager()
    visa_list = rm.list_resources()
    for addr in visa_list:
        if not addr.startswith(prev_addr):
            prev_addr = addr
            try:
                i = rm.open_resource(addr, open_timeout=50, timeout=0.1)
            except visa.VisaIOError:
                # Could not create visa instrument object
                skipped.append(addr)
                # print("Skipping {} due to VisaIOError".format(addr))
                continue
            except socket.timeout:
                skipped.append(addr)
                print("Skipping {} due to socket.timeout".format(addr))
                continue

            try:
                idn = i.ask("*IDN?")
                manufac, model, rest = idn.split(',', 2)
                module_name = _find_visa_inst_type(manufac, model)
                params = _ParamDict("<{} '{}'>".format(manufac, model))
                params['visa_address'] = addr
                if module_name:
                    params.module = module_name
                instruments.append(params)
            except visa.VisaIOError:
                skipped.append(addr)
                continue
            except socket.timeout:
                skipped.append(addr)
                continue
            finally:
                i.close()
    return instruments


def list_instruments():
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
    """
    try:
        from .. import visa
        try:
            inst_list = list_visa_instruments()
        except visa.VisaIOError:
            inst_list = []  # Hide visa errors
    except (ImportError, ConfigError):
        inst_list = []  # Ignore if (Fake)VISA not installed or configured

    for mod_name in _acceptable_params:
        try:
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
    from .. import visa

    if 'visa_address' not in params:
        raise InstrumentTypeError()
    addr = params['visa_address']

    # Check cache to see if we've already found (or not found) the instrument
    if '**visa_instrument' in params:
        visa_inst = params['**visa_instrument']
        if visa_inst is None:
            raise InstrumentNotFoundError("Error: device with address '" +
                                          addr + "' not found!")
    else:
        try:
            rm = visa.ResourceManager()
            visa_inst = rm.open_resource(addr, open_timeout=50)
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
    # Allow passthrough of existing instruments
    if isinstance(inst, Instrument):
        return inst
    elif isinstance(inst, dict):
        params = inst
    else:
        alias = inst

        # Load parameters
        if not alias:
            params = kwargs
        else:
            params = conf.instruments.get(alias, None)
            if params is None:
                raise Exception("Instrument with alias `{}` not ".format(alias)
                                + "found in config file")

    if 'module' in params:
        # We've already been given the name of the module
        # SHOULD PROBABLY INTEGRATE THIS WITH THE OTHER CASE
        try:
            mod = import_module('.' + params['module'], __package__)
        except Exception:
            raise Exception("Specified module '{}' could not be imported".format(params['module']))

        try:
            new_inst = mod._instrument(params)
        except InstrumentTypeError:
            raise Exception("Instrument is not compatible with the given module")
        return new_inst

    # Find the right type of Instrument to create
    has_valid_params = False
    for mod_name, acceptable in _acceptable_params.items():
        if _has_acceptable_params(acceptable, params):
            has_valid_params = True

            # Try to import module, skip it if optional deps aren't met
            try:
                mod = import_module('.' + mod_name, __package__)
            except Exception:
                #print(e.args)
                #print("\tModule {} not supported, skipping".format(mod_name))
                continue

            # Try to create an instance of this instrument type
            try:
                new_inst = mod._instrument(params)
            except AttributeError:
                # Module doesn't define the required _instrument() function
                #print("\tModule " + mod_name +
                #      " missing _instrument(), skipping")
                continue
            except InstrumentTypeError:
                #print("\tNot the right type")
                continue
            except InstrumentNotFoundError:
                #print("\tInstrument not found")
                continue

            return new_inst

    # If we reach this point, we haven't been able to create a valid instrument
    if not has_valid_params:
        raise Exception("Parameters {} match no existing driver module".format(params))
    else:
        raise Exception("No instrument matching {} was found".format(params))
