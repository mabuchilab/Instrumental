# -*- coding: utf-8 -*-
# Copyright 2013-2017 Nate Bogdanowicz
"""
Driver module for New Focus laser controllers

* 6200 ECDL controller

"""
import visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from time import time, sleep
from . import Laser
from .. import VisaMixin, SCPI_Facet
from ..util import visa_context
from ... import u, Q_


INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'NF6200': ('NewFocus', ['57718','6202','6262']),
}


class NF6200(Laser, VisaMixin):
    """
    A base class for New Focus laser controllers. At least works with 6200 series.
    """

    def _initialize(self):
        self.lm_max = Q_(self.query('source:wavelength? max')+'nm')
        self.lm_min = Q_(self.query('source:wavelength? min')+'nm')
        self.laser_on = bool(int(self.query('output:state?')))
        self.lm_setpoint = Q_(self.query('source:wavelength?')+'nm')
        self.lm_start = Q_(self.query('source:wavelength:start?')+'nm')
        self.lm_stop = Q_(self.query('source:wavelength:stop?')+'nm')
        self.slew_rate_forward = float(self.query('source:wavelength:slewrate:forward?'))
        self.slew_rate_return = float(self.query('source:wavelength:slewrate:return?'))
        self.current_setpoint = Q_(self.query('source:current:level:diode?')+'mA')
        self.temperature_setpoint = Q_(float(self.query('source:temperature:level:diode?')),u.degC)
        self.piezo_voltage_setpoint = Q_(self.query('source:voltage:level:piezo?')+'V')


    def operation_complete(self):
        return bool(int(self.query('*OPC?')))

    def start_scan(self,wait=True,t_max=5*u.minute):
        self.write('output:scan:start')
        if wait:
            t0 = time()
            sleep(0.1)
            while ((not self.operation_complete) and ((time()-t0)<t_max.to(u.second).m)):
                sleep(0.2)
            if (not self.operation_complete):
                print('Warning: New Focus 6200 scan+wait operation timed out before scan completed')

    def pause_scan(self):
        self.write('output:scan:stop')

    def reset_scan(self,wait=True,t_max=5*u.minute):
        self.write('output:scan:reset')
        if wait:
            t0 = time()
            sleep(0.1)
            while ((not self.operation_complete) and ((time()-t0)<t_max.to(u.second).m)):
                sleep(0.2)
            if (not self.operation_complete):
                print('Warning: New Focus 6200 scan-reset+wait operation timed out before scan-reset completed')


    def set_laser_on(self):
        self.write('output:state 1')
        self.laser_on = True

    def track_off(self):
        self.write('output:track off')

    def set_laser_off(self):
        self.write('output:state 0')
        self.laser_on = False

    def set_current(self,current):
        self.write('source:current:level:diode {:4.3f}'.format(current.to(u.milliampere).m))
        self.current_setpoint = current.to(u.milliampere)

    def set_temperature(self,temperature):
        self.write('source:temperature:level:diode {:3.3f}'.format(temperature.to(u.degC).m))
        self.temperature_setpoint = temperature.to(u.degC)

    def set_piezo_voltage(self,piezo_voltage):
        self.write('source:voltage:level:piezo {:4.3f}'.format(piezo_voltage.to(u.volt).m))
        self.piezo_voltage_setpoint = piezo_voltage.to(u.volt)

    def set_wavelength(self,wavelength):
        self.write('source:wavelength {:4.3f}'.format(wavelength.to(u.nm).m))
        self.wavelength_setpoint = wavelength.to(u.nm)

    def set_start_wavelength(self,lm_start):
        self.write('source:wavelength:start {:4.3f}'.format(lm_start.to(u.nm).m))
        self.lm_start = lm_start.to(u.nm)

    def set_stop_wavelength(self,lm_stop):
        self.write('source:wavelength:stop {:4.3f}'.format(lm_stop.to(u.nm).m))
        self.lm_stop = lm_stop.to(u.nm)

    def set_slew_rate_forward(self,slew_rate):
        self.write('source:wavelength:slewrate:forward {:3.3f}'.format(slew_rate))
        self.slew_rate_forward = slew_rate

    def set_slew_rate_return(self,slew_rate):
        self.write('source:wavelength:slewrate:return {:3.3f}'.format(slew_rate))
        self.slew_rate_return = slew_rate

    def check_current_setpoint(self):
        current = float(self.query('source:current:level:diode?'))*u.milliampere
        self.current_setpoint = current
        return current

    def check_temperature_setpoint(self):
        temperature = Q_(float(self.query('source:temperature:level:diode?')),u.degC)
        self.temperature_setpoint = temperature
        return temperature

    def check_piezo_voltage_setpoint(self):
        piezo_voltage = float(self.query('source:voltage:level:piezo?'))*u.volt
        self.piezo_voltage_setpoint = piezo_voltage
        return piezo_voltage

    def check_wavelength_setpoint(self):
        lm_set = float(self.query('source:wavelength?'))*u.nm
        self.lm_setpoint = lm_set
        return lm_set

    def check_start_wavelength(self):
        lm_start = float(self.query('source:wavelength:start?'))*u.nm
        self.lm_start = lm_start
        return lm_start

    def check_stop_wavelength(self):
        lm_stop = float(self.query('source:wavelength:stop?'))*u.nm
        self.lm_stop = lm_stop
        return lm_stop

    def check_slew_rate_forward(self):
        slew_rate = float(self.query('source:wavelength:slewrate:forward?'))
        self.slew_rate_forward = slew_rate
        return slew_rate

    def check_slew_rate_return(self):
        slew_rate = float(self.query('source:wavelength:slewrate:return?'))
        self.slew_rate_return = slew_rate
        return slew_rate

    def get_current(self):
        return float(self.query('sense:current:level:diode'))*u.milliampere

    def get_diode_temperature(self):
        return Q_(float(self.query('sense:temperature:level:diode')),u.degC)

    def get_cavity_temperature(self):
        return Q_(float(self.query('sense:temperature:level:cavity')),u.degC)

    def get_piezo_voltage(self):
        return float(self.query('sense:voltage:level:piezo'))*u.volt

    def get_auxiliary_voltage(self):
        return float(self.query('sense:voltage:level:auxiliary'))*u.volt

    def get_wavelength(self):
        return float(self.query('sense:wavelength'))*u.nm

    def get_power(self,facet='front'):
        """
        Get measured power from laser head.
        'facet' can be 'front' or 'rear'
        """
        return float(self.query('sense:power:level:'+facet))*u.mW
