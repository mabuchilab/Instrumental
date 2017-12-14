# -*- coding: utf-8 -*-
# Copyright 2014-2017 Dodd Gray, Nate Bogdanowicz
"""
Driver for VISA control of HC Photonics TC038 temperature controller
"""

#import numpy as np
from ... import u, Q_ #, visa
from .. import _get_visa_instrument, _ParamDict
from . import TempController
from pyvisa.constants import *
import time

#import visa
#from pint import unit
#from .. import _get_visa_instrument
#from .. import InstrumentTypeError
#from ... import visa

def _instrument(params):
    inst = _get_visa_instrument(params)
    # Should add a check of instrument type here. Not sure how to do this now,
    # since querying '*IDN?' doesn't work.
    return TC038(inst)


#TC038 = visa.instrument('HCPhotonics_TC038_TempCont')
#TC038.parity = 2
#example_temp = 3*u.degC
#
#def ask_SetTemp():
#    return int('0X' + TC038.ask('\x0201010WRDD0003,01\x03')[7:11],0)/10.0  * u.degC
#
#
#def set_SetTemp(set_temp_in):
#    if type(set_temp_in) != int and type(set_temp_in) != float and set_temp_in.dimensionality == example_temp.dimensionality:
#        if 20*u.degC< set_temp_in <= 200*u.degC:
#            TC038.ask('\x0201010WWRD0120,01,{:04X}\x03'.format(int(round(10*set_temp_in.to(u.degC).magnitude))))
#        else:
#            print('SHIT. Well great job, you broke it. Set_Temp input not in valid range (20-200C)')
#    else:
#        print ('units, bro. DegC')
#
#def ask_CurrentTemp():
#    return int('0X' + TC038.ask('\x0201010WRDD0002,01\x03')[7:11],0)/10.0 * u.degC
#
class TC038(TempController):
    """Class definition for an HC Photonics TC038 temperature controller."""

    def __init__(self, visa_inst):

            self._inst = visa_inst
            self._inst.parity = Parity.even
            #self._inst.write_termination = '\r'
            #self._inst.read_termination = '\r'
            self._inst.ignore_warning(VI_SUCCESS_MAX_CNT)   # So far I've only had success reading
                                                            # the output buffer when I specify the
                                                            # exact number of waiting bytes as the
                                                            # read length (otherwise it times out).
                                                            # Sometimes pyvisa throws a warning when
                                                            # you read like this, so I try suppress those.
                                                            # For some reason this doesn't seem to work. Will fix later.
            # Parameter dicitonary for saving
            self._param_dict = _ParamDict({})
            self._param_dict['visa_address'] = str(self._inst.resource_name)  # maybe a bad way to do this
            self._param_dict['module'] = 'tempcontrollers.hcphotonics'


    def bytes_in_buffer(self):
        return self._inst.bytes_in_buffer

    def current_temp(self):
        self._inst.write('\x0201010WRDD0002,01\x03')
        time.sleep(0.1)
        output_raw = self._inst.visalib.read(self._inst.session,count=self._inst.bytes_in_buffer)
        temp = Q_(int('0X' + output_raw[0][7:11],0)/10.0,u.degC)
        return temp

    def set_set_temp(self, set_temp):
        set_temp_degC = set_temp.to(u.degC)
        if Q_(20,u.degC)< set_temp <= Q_(200,u.degC):
            self._inst.write('\x0201010WWRD0120,01,{:04X}\x03'.format(int(round(10*set_temp_degC.magnitude))))
        else:
            raise Exception('set_temp input not in valid range (20-200C)')
        time.sleep(0.1)
        output_raw = self._inst.visalib.read(self._inst.session,count=self._inst.bytes_in_buffer)[0]
        return output_raw

    def get_set_temp(self):
        self._inst.write('\x0201010WRDD0003,01\x03')
        time.sleep(0.1)
        output_raw = self._inst.visalib.read(self._inst.session,count=self._inst.bytes_in_buffer)
        temp = Q_(int('0X' + output_raw[0][7:11],0)/10.0,u.degC)
        return temp

    def close(self):
        self._inst.close()
