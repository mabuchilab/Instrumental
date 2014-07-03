# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from .. import conf
from importlib import import_module

# Listing of acceptable parameters for each driver module
_acceptable_params = {
    'cameras.uc480':
        ['ueye_cam_id', 'cam_serial', 'cam_model'],
    'funcgenerators.tektronix':
        ['visa_address'],
    'scopes.tektronix':
        ['visa_address']
}

_visa_models = {
    'funcgenerators.tektronix':(
        'TEKTRONIX',
        ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102',
         'AFG3251', 'AFG3252']
    ),
    'scopes.tektronix':(
        'TEKTRONIX',
        ['TDS 3032', 'TDS 3034B', 'MSO4034', 'DPO4034']
    )
}


class InstrumentTypeError(Exception):
    pass


class InstrumentNotFoundError(Exception):
    pass


class Instrument(object):
    """
    Instrumental instrument class for VISA instruments. Not to be confused
    with an VISA instrument object. Possibly to be renamed...
    Should we include Thorlabs cameras, which aren't VISA-controlled?
    Probably not.
    """
    pass


def _find_visa_inst_type(manufac, model):
    for mod_name, tup in _visa_models.items():
        mod_manufac, mod_models = tup
        if manufac == mod_manufac and model in mod_models:
            return mod_name
    return None


def list_visa_instruments():
    from .. import visa
    skipped = []
    prev_addr = 'START'
    visa_list = visa.get_instruments_list()
    for addr in visa_list:
        if not addr.startswith(prev_addr):
            prev_addr = addr
            i = visa.instrument(addr, timeout=0.1)
            try:
                idn = i.ask("*IDN?")
                manufac, model, rest = idn.split(',', 2)
                module_name = _find_visa_inst_type(manufac, model)
                type_name = module_name if module_name else "Not recognized"
                print("{}\t{}\t{}".format(manufac, model, type_name))
            except visa.VisaIOError:
                skipped.append(addr)
            i.close()


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
            visa_inst = visa.instrument(addr)
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
    """
    # Allow passthrough of existing instruments
    if isinstance(inst, Instrument):
        return inst
    else:
        alias = inst

    # Load parameters
    if not alias:
        params = kwargs
    else:
        params = conf.instruments.get(alias, None)
        if params is None:
            raise Exception("Instrument with alias `{}` not ".format(alias) +
                            "found in config file")

    # Find the right type of Instrument to create
    has_valid_params = False
    for mod_name, acceptable in _acceptable_params.items():
        if _has_acceptable_params(acceptable, params):
            has_valid_params = True

            # Try to import module, skip it if optional deps aren't met
            try:
                mod = import_module('.' + mod_name, __package__)
            except ImportError as e:
                #print(e.args)
                #print("\tModule {} not supported, skipping".format(mod_name))
                continue

            # Try to create an instance of this instrument type
            try:
                new_inst = mod._instrument(params)
                return new_inst
            except AttributeError:
                # Module doesn't define the required _instrument() function
                #print("\tModule " + mod_name +
                #      " missing _instrument(), skipping")
                pass
            except InstrumentTypeError:
                #print("\tNot the right type")
                pass
            except InstrumentNotFoundError:
                #print("\tInstrument not found")
                pass

    # If we reach this point, we haven't been able to create a valid instrument
    if not has_valid_params:
        raise Exception("Parameters {} match no existing driver module".format(params))
    else:
        raise Exception("No instrument matching {} was found".format(params))
