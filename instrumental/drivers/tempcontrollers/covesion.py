# -*- coding: utf-8 -*-
"""
Driver for VISA control of OC2 crystal oven temperature controller
Created on Tue Sep 16 2017

@author: dodd
"""


from ... import u, Q_ #, visa
from .. import _get_visa_instrument, ParamSet
from . import TempController
#from .. import VisaMixin, SCPI_Facet
#from ..util import visa_context
from pyvisa.constants import *
from pyvisa import ResourceManager
import time
from datetime import timedelta
from sys import stdout
import codecs
import numpy as np
from time import sleep
#import visa
#from pint import unit
#from .. import _get_visa_instrument
#from .. import InstrumentTypeError
#from ... import visa

# def _instrument(params):
#     inst = _get_visa_instrument(params)
#     # Should add a check of instrument type here. Not sure how to do this now,
#     # since querying '*IDN?' doesn't work.
#     return OC(inst)
_INST_PARAMS = ['OC_visa_address','version']
_INST_CLASSES = ['OC']
#rm = ResourceManager()
OC_parity = Parity.none
OC_baud_rate = 19200
OC_data_bits = 8
OC_read_termination = '\r'
OC_flow_control = 0
OC_timeout = 500
OC_status_keys =  ['set point',
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
rm = ResourceManager()
def print_statusline(msg: str):
    last_msg_length = len(print_statusline.last_msg) if hasattr(print_statusline, 'last_msg') else 0
    print(' ' * last_msg_length, end='\r')
    print(msg, end='\r')
    stdout.flush()
    print_statusline.last_msg = msg

def _open_visa_OC(rm,visa_address):
    visa_inst = rm.get_instrument(visa_address)
    visa_inst.parity = OC_parity # = Parity.none
    visa_inst.baud_rate = OC_baud_rate # = 19200
    visa_inst.data_bits = OC_data_bits # = 8
    visa_inst.read_termination = OC_read_termination # = '\r'
    visa_inst.flow_control = OC_flow_control # = 0
    visa_inst.timeout = OC_timeout # = 10000
    visa_inst.clear()
    return visa_inst

def _check_OC(rm,visa_address,n_tries_max=5):
    n_tries = 0
    success = False
    version = False
    while not(success) and (n_tries < n_tries_max):
        try:
            visa_inst = _open_visa_OC(rm,visa_address)
            output_raw = visa_inst.ask('\X01J00\X00\XCB')
            visa_inst.close()
            success = True
            vals = output_raw[5:-3].split(';')
            status_dict = dict(zip(OC_status_keys,vals))
            version = status_dict['version']
        except:
            pass
        n_tries = n_tries + 1
    return version
    #
    #return dict(zip(self.status_keys,vals))

def list_instruments():
    instruments = []
    #rm = ResourceManager()
    visa_list = rm.list_resources()
    for addr in visa_list:
        if addr[0:4]=='ASRL':
            version = _check_OC(rm,addr)
            if version:
                params = ParamSet(OC,OC_visa_address=addr,version=version)
                instruments.append(params)
    #rm.close()
    return instruments


class OC(TempController):
    """Class definition for a Covesion OC1 and OC2 oven temperature controllers."""

    def _initialize(self):
            self.visa_address = self._paramset['OC_visa_address']
            self.version = self._paramset['version']
            self.parity = OC_parity
            self.baud_rate = OC_baud_rate
            self.data_bits = OC_data_bits
            self.read_termination = OC_read_termination
            self.flow_control = OC_flow_control
            self.timeout = OC_timeout
            self.status_keys =  OC_status_keys
            self.drive_str = '\x01m041;0;A9'
            #self.rm = ResourceManager()
            # Parameter dicitonary for saving
            #self._param_dict = _ParamDict({})
            #self._param_dict['visa_address'] = self.visa_address #str(self._inst.resource_name)  # maybe a bad way to do this
            #self._param_dict['module'] = 'tempcontrollers.covesion'

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

    def get_status(self,n_tries_max=50):
        n_tries = 0
        success = False
        while not(success) and (n_tries < n_tries_max):
            try:
                visa_inst = self.open_visa()
                output_raw = visa_inst.ask('\X01J00\X00\XCB')
                visa_inst.close()
                success = True
            except:
                pass
            n_tries = n_tries + 1
        vals = output_raw[5:-3].split(';')
        return dict(zip(self.status_keys,vals))

    def get_current_temp(self,n_tries_max=20):
        n_tries = 0
        while (n_tries < n_tries_max):
            try:
                return Q_(float(self.get_status()['temperature']),u.degC)
            except:
                sleep(0.5)
                n_tries +=1

    def get_set_temp(self,n_tries_max=20):
        n_tries = 0
        while (n_tries < n_tries_max):
            try:
                return Q_(float(self.get_status()['set point']),u.degC)
            except:
                sleep(0.5)
                n_tries +=1

    def _set_set_temp(self, set_temp):
        set_temp_degC = set_temp.to(u.degC).magnitude
        if Q_(20,u.degC)< set_temp <= Q_(200,u.degC):
            if set_temp < Q_(100,u.degC):
                cmd_str = '\x01i371;{:.3f};25.000;0.000;25;100.00;0.00;'.format(set_temp_degC)
            else:
                cmd_str = '\x01i381;{:.3f};25.000;0.000;25;100.00;0.00;'.format(set_temp_degC)
            #cmd_bytes = bytes(cmd_str,encoding='utf8')
            checksum_str = format( sum(ord(ch) for ch in cmd_str)%256,'x')
            cmd_str += checksum_str
            #cmd_str = codecs.decode(cmd_str,'unicode_escape')
            visa_inst = self.open_visa()
            visa_inst.visalib.set_buffer(visa_inst.session,48,100)
            visa_inst.flush(16)
            visa_inst.write_raw(cmd_str)
            visa_inst.write_raw(self.drive_str)
            visa_inst.close()
        else:
            raise Exception('set_temp input not in valid range (20-200C)')
        return

    def set_set_temp(self,set_temp):
        current_temp = self.get_current_temp()
        print('current_temp: {}'.format(current_temp))
        print('set_temp: {}'.format(set_temp))
        delta_temp_degC = np.abs(set_temp - current_temp).magnitude
        if delta_temp_degC > 10:
            n_comm = round(delta_temp_degC/10) + 1
            T_comm = np.linspace(current_temp.to(u.degC).magnitude,
                                 set_temp.to(u.degC).magnitude,
                                 n_comm+1
                                )
            T_step = T_comm[1] - T_comm[0]
            t_step = abs(T_step / 10.0 * 60) # number of seconds to wait between steps, targeting ~10C/min
            T_comm = Q_(T_comm[1:],u.degC)
            for Tind, TT in enumerate(T_comm):
                print_statusline('\rapproaching temp: {:3.2f}C from {:3.2f}C, step {} of {}...'.format(float(set_temp.to(u.degC).magnitude), float(current_temp.to(u.degC).magnitude),Tind+1,n_comm))
                self._set_set_temp(TT)
                sleep(t_step)
            return
        else:
            self._set_set_temp(set_temp)
            return

    def set_temp_and_wait(self,set_temp,max_err=Q_(0.1,u.degK),n_samples=10,timeout=5*u.minute):
        self.set_set_temp(set_temp)
        err = np.ones((n_samples)) * 10.0 * max_err
        count = 0
        t0 = time.time()
        while (err.to(u.degK).magnitude > max_err.to(u.degK).magnitude).any() and ((time.time()-t0) < timeout.to(u.second).magnitude):
            err[0:n_samples-1] = err[1:]
            current_error = (self.get_current_temp() - set_temp).to(u.degK)
            err[n_samples-1] = np.abs(current_error)
            print_statusline('\rapproaching temp: {:3.2f}C, current temp error: {:3.2f}, time elapsed: '.format(float(set_temp.to(u.degC).magnitude), float(current_error.magnitude)) + str(timedelta(seconds=int(time.time()-t0))))
        if (time.time()-t0) > timeout.to(u.second).magnitude:
            raise Exception('Timeout while waiting for Covesion OC1 to reach set temperature {:3.2f}C'.format(set_temp.to(u.degC).magnitude))
        else:
            print_statusline('temperature {:3.2f}C reached in {:3.1f}s'.format(set_temp.to(u.degC).magnitude,time.time()-t0))
        return
