# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz
"""
Package containing a driver module/class for supported function generators.
"""

from .. import InstrumentTypeError
from ... import visa

class FunctionGenerator(object):
    pass

# Must import after FunctionGenerator, which AFG3000 needs
from .AFG3000 import AFG3000, AFG3000_models

def funcgen(fgen):
    """ Create a function generator object from an address or existing object """
    if isinstance(fgen, FunctionGenerator):
        # We were already given a valid function generator object; return it
        return fgen
    elif isinstance(fgen, visa.Instrument):
        # We were given a raw VISA object
        inst = fgen
    else:
        name = fgen
        try:
            inst = visa.instrument(name)
        except visa.VisaIOError as e:
            print("Error: device with address '{}' not found!".format(name))
            return None
    idn = inst.ask("*IDN?")
    idn_list = idn.split(',')

    if idn_list[0] == 'TEKTRONIX':
        model = idn_list[1]
        if model in AFG3000_models:
            return AFG3000(inst)

    raise InstrumentTypeError("Error: unsupported instrument with IDN = '{}'".format(idn))
