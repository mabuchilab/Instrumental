# -*- coding: utf-8 -*-
"""
Driver module for Rigol oscilloscopes. Currently supports

* DS1000Z series
"""
import visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from . import Scope
from .. import VisaMixin, SCPI_Facet, Facet
from ..util import visa_context
from ... import u, Q_
from enum import Enum
from .. import ParamSet
from visa import ResourceManager
from enum import Enum
import time
import numpy as np
from struct import unpack

_INST_PARAMS_ = ['visa_address']
_INST_VISA_INFO_ = {
    'DS1000Z': ('RIGOL TECHNOLOGIES', ['DS1054Z']),
}

MANUFACTURER_ID = 0x1AB1

class SpecTypes(Enum):
    DS1054Z = 0x04CE

def list_instruments():
    """Get a list of all spectrometers currently attached"""
    paramsets = []
    model_string = ''

    for spec in SpecTypes:
        model_string += '(VI_ATTR_MODEL_CODE==0x{:04X}) || '.format(spec.value)
    model_string = model_string.rstrip(' || ')
    search_string = "USB?*?{{VI_ATTR_MANF_ID==0x{:04X} && ({})}}".format(MANUFACTURER_ID, model_string)

    rm = ResourceManager()
    try:
        raw_spec_list = rm.list_resources(search_string)
    except:
        return paramsets

    for spec in raw_spec_list:
        _, _, model, serial, _ = spec.split('::', 4)
        model = SpecTypes(int(model, 0))
        paramsets.append(ParamSet(DS1000Z, usb=spec, serial=serial, model=model))

    return paramsets

class OnOffState(Enum):
    ON = True
    OFF = False

class RigolScope(Scope, VisaMixin):
    """
    A base class for Rigol Technologies Scopes
    """

    yinc = SCPI_Facet(':WAVeform:YINCrement', convert=float)
    yref = SCPI_Facet(':WAVeform:YREFerence', convert=float)
    yorig = SCPI_Facet(':WAVeform:YORigin', convert=float)
    xincr = SCPI_Facet(':WAVeform:XINCrement', convert=float)
    beeper = SCPI_Facet('SYSTem:BEEPer', convert=OnOffState)

    def _initialize(self):
        self._rsrc.write_termination = '\n'
        self._rsrc.read_termination = '\n'

    @property
    def manufacturer(self):
        manufacturer, _, _, _ = self.query('*IDN?').rstrip().split(',', 4)
        return manufacturer

    @property
    def model(self):
        _, model, _, _ = self.query('*IDN?').split(',', 4)
        return model

    @property
    def serial(self):
        _, _, serial, _ = self.query('*IDN?').split(',', 4)
        return serial

    @property
    def version(self):
        _, _, _, version = self.query('*IDN?').rstrip().split(',', 4)
        return version

    @property
    def beeper(self):
        val = self.query('SYSTem:BEEPer?')
        return OnOffState[val].value

    @beeper.setter
    def beeper(self, val):
        val = int(bool(val))
        self.write('SYSTem:BEEPer %s' % OnOffState(val).name)

    @property
    def vmax_averages(self):
        return self.query(':MEASure:STATistic:ITEM? AVERages,VMAX')

    @property
    def vmax(self):
        return self.query(':MEASure:ITEM? VMAX')

    @property
    def vmin_averages(self):
        return self.query(':MEASure:STATistic:ITEM? AVERages,VMIN')

    @property
    def vmin(self):
        return self.query(':MEASure:ITEM? VMIN')

    def get_data(self):
        self.write(':WAV:SOUR CHAN1')
        time.sleep(1)
        data = self._rsrc.query_binary_values(':WAVeform:DATA?', datatype='B')

        yinc = self.yinc # Don't query multiple times
        yref = self.yref
        yorig = self.yorig
        xincr = self.xincr

        Volts = [(val - yorig - yref) * yinc for val in data]
        Time = np.arange(0, xincr * len(Volts), xincr)

        return Time, Volts

    def single_acq(self):
        self.write("STOP")
        self.write(":FUNCtion:WRECord:ENABle 0")
        self.write(":FUNCtion:WRECord:ENABle 1")
        self.write("RUN")
        while True:  # 1 means that the acquisition is still running
            time.sleep(0.5)
            if self.query(":FUNCtion:WRECord:OPERate?") == "STOP":
                self.write(":FUNCtion:WRECord:ENABle 0")
                break

    def local(self):
        self.write('SYSTem:LOCal')

    def remote(self):
        self.write('SYSTem:REMote')


class DS1000Z(RigolScope, VisaMixin):
    pass