# -*- coding: utf-8 -*-
# Copyright 2019 Jonathan Wheeler, Christopher Zee
"""
Driver module for Rigol signal generators.
"""
from enum import Enum, auto
from . import FunctionGenerator
from .. import VisaMixin, SCPI_Facet
from .. import ParamSet
from visa import ResourceManager

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'DG800': ('Rigol Technologies', ['DG811', 'DG812']),
}

MANUFACTURER_ID = 0x1AB1


class SpecTypes(Enum):
    DG811 = 0x0643


class Waveform(Enum):
    PULSe = auto()


def list_instruments():
    """Get a list of all spectrometers currently attached"""
    paramsets = []
    model_string = '|'.join('{:04X}'.format(spec.value) for spec in SpecTypes)
    search_string = "USB[0-9]*::0x{:04X}::0x({})".format(MANUFACTURER_ID, model_string)
    rm = ResourceManager()

    try:
        raw_spec_list = rm.list_resources(search_string)
    except:
        return paramsets

    for spec in raw_spec_list:
        _, _, model, serial, _ = spec.split('::', 4)
        model = SpecTypes(int(model, 0))
        paramsets.append(ParamSet(DG800, usb=spec, serial=serial, model=model))

    return paramsets


class RigolFunctionGenerator(FunctionGenerator, VisaMixin):
    def _initialize(self):
        self._rsrc.read_termination = '\n'


class OnOffState(Enum):
    ON = True
    OFF = False


class DG800(RigolFunctionGenerator, VisaMixin):
    frequency1 = SCPI_Facet('SOURce1:FREQuency', convert=float, units='Hz')
    frequency2 = SCPI_Facet('SOURce2:FREQuency', convert=float, units='Hz')
    amplitude1 = SCPI_Facet('SOURce1:VOLTage:AMPlitude', convert=float, units='V')
    amplitude2 = SCPI_Facet('SOURce2:VOLTage:AMPlitude', convert=float, units='V')
    offset1 = SCPI_Facet('SOURce1:VOLTage:OFFSet', convert=float, units='V')
    offset2 = SCPI_Facet('SOURce2:VOLTage:OFFSet', convert=float, units='V')
    phase1 = SCPI_Facet('SOURce1:PHASe', convert=float, units='deg')
    phase2 = SCPI_Facet('SOURce2:PHASe', convert=float, units='deg')
    width1 = SCPI_Facet('SOURce1:FUNCtion:PULSe:WIDTh', convert=float, units='s')
    width2 = SCPI_Facet('SOURce2:FUNCtion:PULSe:WIDTh', convert=float, units='s')
    waveform1 = SCPI_Facet('SOURce1:FUNCtion')
    waveform2 = SCPI_Facet('SOURce2:FUNCtion')
    duty_cycle1 = SCPI_Facet('SOURce1:FUNCtion:PULSe:DCYC', convert=float)
    duty_cycle2 = SCPI_Facet('SOURce2:FUNCtion:PULSe:DCYC', convert=float)
    output1 = SCPI_Facet('OUTPut1:STATe', convert=OnOffState)
    output2 = SCPI_Facet('OUTPut2:STATe', convert=OnOffState)

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

    @property
    def output1(self):
        val = self.query('OUTPut1:STATe?')
        return OnOffState[val].value

    @output1.setter
    def output1(self, val):
        val = int(bool(val))
        self.write('OUTPut1:STATe %s' % OnOffState(val).name)

    @property
    def output2(self):
        val = self.query('OUTPut2:STATe?')
        return OnOffState[val].value

    @output2.setter
    def output2(self, val):
        val = int(bool(val))
        self.write('OUTPut2:STATe %s' % OnOffState(val).name)

    def align(self):
        # /*Executes an align phase operation on CH1.*/
        self._rsrc.write(':SOUR1:PHAS:INIT')

        # /*Executes an align phase operation on CH2.*/
        # :SOUR2:PHAS:SYNC

    def apply1(self, waveform, frequency=None, amplitude=None, offset=None, phase=None):
        self.write('SOURce1:APPLy:{} {},{},{},{}'.format(Waveform(waveform).name, frequency, amplitude, offset, phase))

    def local(self):
        self.write('SYSTem:LOCal')

    def remote(self):
        self.write('SYSTem:REMote')
