# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz
class InstrumentTypeError(Exception):
    pass

from .. import settings
from .. import visa
from scopes import scope

class Instrument(object):
    """
    Instrumental instrument class for VISA instruments. Not to be confused 
    with an VISA instrument object. Possibly to be renamed...
    Should we include Thorlabs cameras, which aren't VISA-controlled?
    Probably not.
    """
    pass


def instrument(name):
    """
    Function to create any Instrumental instrument object from an alias or
    address.
    """
    if name in settings['instruments'].keys():
        addr = settings['instruments'][name]
    else:
        addr = name
    visa_inst = visa.instrument(addr)
    inst = None

    # Find the right type of Instrument to create
    for func in [scope]:
        try:
            inst = func(visa_inst)
            break
        except InstrumentTypeError as e:
            pass # Continue and try next type

    if not inst:
        idn = visa_inst.ask("*IDN?")
        raise InstrumentTypeError("Error: Instrument '{}' not supported".format(idn))

    return inst
