# -*- coding: utf-8 -*-

from . import PowerSupply
from .. import VisaMixin, Facet, SCPI_Facet
from ... import u, Q_
from .. import ParamSet
from enum import Enum
from visa import ResourceManager
import pyvisa
import re

_INST_PARAMS_ = ['visa_address']
_INST_VISA_INFO_ = {
    'DP700': ('RIGOL TECHNOLOGIES', ['DP711', 'DP712']),
}

def list_instruments():
    """Get a list of all power supplies currently attached"""
    paramsets = []
    search_string = "ASRL?*"
    rm = ResourceManager()
    raw_spec_list = rm.list_resources(search_string)

    for spec in raw_spec_list:
        try:
            inst = rm.open_resource(spec, read_termination='\n', write_termination='\n')
            idn = inst.query("*IDN?")
            manufacturer, model, serial, version = idn.rstrip().split(',', 4)
            if re.match('DP7[0-9]{2}', model):
                paramsets.append(ParamSet(DP700, asrl=spec, manufacturer=manufacturer, serial=serial, model=model, version=version))
        except pyvisa.errors.VisaIOError as vio:
            # Ignore unknown serial devices
            pass

    return paramsets

class OnOffState(Enum):
    ON = True
    OFF = False

class RigolPowerSupply(PowerSupply, VisaMixin):
    def _initialize(self):
        self._rsrc.write_termination = '\n'
        self._rsrc.read_termination = '\n'

class DP700(RigolPowerSupply, VisaMixin):
    voltage = SCPI_Facet('SOURce:VOLTage:LEVel:IMMediate:AMPLitude', convert=float, units='V')
    current = SCPI_Facet('SOURce:CURRent:LEVel:IMMediate:AMPLitude', convert=float, units='A')
    current_protection = SCPI_Facet('SOURce:CURRent:PROTection', convert=float, units='A')
    current_protection_state = SCPI_Facet('SOURce:CURRent:PROTection:STATe', convert=OnOffState)
    output = SCPI_Facet('OUTPut:STATe', convert=OnOffState)
    beeper = SCPI_Facet('SYSTem:BEEPer', convert=OnOffState)

    @property
    def manufacturer(self):
        manufacturer, _, _, _ = self.query('*IDN?').rstrip().split(',', 4)
        return manufacturer

    @property
    def model(self):
        _, model, _, _ = self.query('*IDN?').rstrip().split(',', 4)
        return model

    @property
    def serial(self):
        _, _, serial, _ = self.query('*IDN?').rstrip().split(',', 4)
        return serial

    @property
    def version(self):
        _, _, _, version = self.query('*IDN?').rstrip().split(',', 4)
        return version

    def get_measured_voltage(self):
        return Q_(self.query(':MEASure:VOLTage?'), u.V)

    def get_measured_current(self):
        return Q_(self.query(':MEASure:CURRent?'), u.A)

    @current_protection_state.setter
    def current_protection_state(self, val):
        val = int(bool(val))
        self.write('SOURCE:CURRent:PROTection:STATe %s' % OnOffState(val).name)

    @output.setter
    def output(self, val):
        val = int(bool(val))
        self.write('OUTPut:STATe %s' % OnOffState(val).name)

    @beeper.setter
    def beeper(self, val):
        val = int(bool(val))
        self.write('SYSTem:BEEPer %s' % OnOffState(val).name)

    def local(self):
        self.write('SYSTem:LOCal')

    def remote(self):
        self.write('SYSTem:REMote')