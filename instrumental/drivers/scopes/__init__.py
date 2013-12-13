# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz
"""
Package containing a driver module/class for each supported oscilloscope type.
"""

import visa

SCOPE_A = "TCPIP::171.64.84.116::INSTR"
SCOPE_B = "TCPIP::171.64.85.167::INSTR"

class Scope(object):
    pass

from .tds3032 import TDS_3032 # Must import after Scope, which tds3032 requires

def scope(scope):
    """ Determine the type of scope and automatically create and return its object """
    if isinstance(scope, Scope):
        # We were already given a valid scope
        return scope
    elif isinstance(scope, visa.Instrument):
        inst = scope
    else:
        name = scope
        try:
            inst = visa.instrument(name)
        except visa.VisaIOError as e:
            print("Error: device with address '{}' not found!".format(name))
            return None
    idn = inst.ask("*IDN?")
    idn_list = idn.split(',')

    if idn_list[0] == 'TEKTRONIX':
        model = idn_list[1]
        if model == 'TDS 3032':
            return TDS_3032(instrument=inst)
        elif model == 'MSO4034':
            return TDS_3032(instrument=inst)

    print("Error: unsupported scope with IDN = '{}'".format(idn))
    return None
