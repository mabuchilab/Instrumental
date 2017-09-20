# -*- coding: utf-8 -*-
"""
Driver for VISA control of OC2 crystal oven temperature controller
Created on Tue Sep 16 2017

@author: dodd
"""

#import numpy as np
from ... import u, Q_ #, visa
from .. import _get_visa_instrument, _ParamDict
from . import TempController
from pyvisa.constants import *
from pyvisa import ResourceManager
import time
import codecs

#import visa
#from pint import unit
#from .. import _get_visa_instrument
#from .. import InstrumentTypeError
#from ... import visa

def _instrument(params):
    inst = _get_visa_instrument(params)
    # Should add a check of instrument type here. Not sure how to do this now,
    # since querying '*IDN?' doesn't work.
    return OC(inst)

rm = ResourceManager()


class OC(TempController):
    """Class definition for a Covesion OC1 and OC2 oven temperature controllers."""

    def __init__(self, visa_address):
            self.parity = Parity.none
            self.baud_rate = 19200
            self.data_bits = 8
            self.read_termination = '\r' #self._inst.CR
            self.flow_control = 0
            self.timeout = 10000
            self.visa_address = visa_address
            self.status_keys =  ['set point',
                                 'temperature',
                                 'control',
                                 r'output %',
                                 'alarms',
                                 'faults',
                                 'temp ok',
                                 'supply vdc',
                                 'version',
                                 'test cycle',
                                 'test mode',
                                 ]
            self.drive_str = '\x01m041;0;A9'
            # Parameter dicitonary for saving
            self._param_dict = _ParamDict({})
            self._param_dict['visa_address'] = self.visa_address #str(self._inst.resource_name)  # maybe a bad way to do this
            self._param_dict['module'] = 'tempcontrollers.covesion'

    def open_visa(self):
        visa_inst = rm.get_instrument(self.visa_address)
        visa_inst.parity = self.parity # = Parity.none
        visa_inst.baud_rate = self.baud_rate # = 19200
        visa_inst.data_bits = self.data_bits # = 8
        visa_inst.read_termination = self.read_termination # = '\r'
        visa_inst.flow_control = self.flow_control # = 0
        visa_inst.timeout = self.timeout # = 10000
        visa_inst.clear()
        return visa_inst

    def get_status(self):
        visa_inst = self.open_visa()
        output_raw = visa_inst.ask('\X01J00\X00\XCB')
        visa_inst.close()
        vals = output_raw[5:-3].split(';')
        return dict(zip(self.status_keys,vals))

    def get_current_temp(self):
        return Q_(self.get_status()['temperature'],u.degC)

    def get_set_temp(self):
        return Q_(self.get_status()['set point'],u.degC)

    def set_set_temp(self, set_temp):
        set_temp_degC = set_temp.to(u.degC).magnitude
        if Q_(20,u.degC)< set_temp <= Q_(200,u.degC):
            cmd_str = r'\x01i371;{:5.3f};25.000;0.000;25;100.00;0.00;'.format(set_temp_degC)
            cmd_bytes = bytearray([0x01]) + bytes(cmd_str[4:],encoding='utf8')
            checksum_str = format(sum(cmd_bytes)%256,'x')
            cmd_str += checksum_str
            cmd_str = codecs.decode(cmd_str,'unicode_escape')
            visa_inst = self.open_visa()
            visa_inst.visalib.set_buffer(visa_inst.session,48,100)
            visa_inst.flush(16)
            visa_inst.write_raw(cmd_str)
            visa_inst.write_raw(self.drive_str)
            visa_inst.close()
        else:
            raise Exception('set_temp input not in valid range (20-200C)')
        return
