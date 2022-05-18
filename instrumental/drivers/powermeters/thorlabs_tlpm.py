# -*- coding: utf-8 -*-
# Author Sebastien Weber
# Date 2022/03/07
"""
PyMoDAQ plugin for thorlabs instruments based on the TLPM library allowing
remote control and monitoring of up to eight power and energy meters.
This software is compatible with our Power Meter Consoles and Interfaces (PM100A and PM101 Series),
Power and Energy Meter Consoles and Interfaces (PM100D, PM400, PM100USB, PM103 Series, and legacy PM200),
Position & Power Meter Interfaces (PM102 Series),
Wireless Power Meters (PM160, PM160T, and PM160T-HP),
and USB-Interface Power Meters (PM16 Series)

you have to install the Optical Monitor Software from Thorlabs to obtain the library

The installation should create (following the manual) an environment variable called either VXIPNPPATH64 or
VXIPNPPATH depending on your platform (32 or 64 bits) pointing to where the TLPM library is
(usually C:\Program Files\IVI Foundation\VISA)

"""
from enum import Enum
from instrumental import u, Q_
from instrumental.drivers.powermeters import PowerMeter
from instrumental.log import get_logger
from instrumental.drivers import Facet
from instrumental.drivers import ParamSet
from instrumental.drivers.powermeters._thorlabs.tlpm_midlib import NiceTLPM
from instrumental.drivers.util import check_units, check_enums, as_enum

log = get_logger(__name__)


def list_instruments():
    rsrc = NiceTLPM.Rsrc()
    Nrsrc = rsrc.findRsrc()
    pset = []
    for ind in range(Nrsrc):
        name = rsrc.getRsrcName(ind)
        model_name, serial, manufacturer, isavailable = rsrc.getRsrcInfo(ind)
        pset.append(ParamSet(TLPM, serial=serial.decode(),  model=model_name.decode()))
    return pset


class TLPMError(Exception):
    def __init__(self, message):
        super().__init__(message)


class DeviceInfo:
    def __init__(self, model_name='', serial_number='', manufacturer='', is_available=False):
        self.model_name = model_name
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.is_available = is_available

    def __repr__(self):
        return f'Model: {self.model_name} / SN: {self.serial_number} by {self.manufacturer} is'\
               f' {"" if self.is_available else "not"} available'


class UNITS(Enum):
    W = 0
    dBm = 1


class TLPM(PowerMeter):
    _INST_PARAMS_ = ['serial', 'model']

    unit = UNITS['W']
    init_wavelength = Q_('532nm')

    def _initialize(self):
        """
        """

        rsrc = NiceTLPM.Rsrc()
        Nrsrc = rsrc.findRsrc()
        for ind in range(Nrsrc):
            model_name, serial, manufacturer, isavailable = rsrc.getRsrcInfo(ind)
            if serial == self._paramset['serial'].encode():
                break
        self.name = rsrc.getRsrcName(ind)
        self.index = ind
        self._open(self.name, True)

    def _open(self, name, reset=False):
        """

        """
        self._device = NiceTLPM.Powermeter(name, 1, reset)
        self.wavelength = self.init_wavelength

    def close(self):
        self._device.close()

    def get_device_info(self) -> DeviceInfo:
        name, serial, manufacturer, isavailable = self._device.getRsrcInfo(self.index)
        return DeviceInfo(name.decode(), serial.decode(),
                          manufacturer.decode(), isavailable)
    
    def get_calibration(self) -> str:
        return self._device.getCalibrationMsg().decode()

    @Facet(type=lambda x: as_enum(UNITS, x))
    def power_unit(self):
        unit_int = self._device.getPowerUnit()
        self.unit = UNITS(unit_int)
        return self.unit

    @power_unit.setter
    def power_unit(self, unit='W'):
        self._device.setPowerUnit(unit.value)
        self.unit = unit

    def get_power(self):
        return Q_(self._device.measPower(), self.unit.name)

    def get_wavelength_range(self):
        lmin = Q_(self._device.getWavelength(NiceTLPM._defs['TLPM_ATTR_MIN_VAL']), 'nm')
        lmax = Q_(self._device.getWavelength(NiceTLPM._defs['TLPM_ATTR_MAX_VAL']), 'nm')
        return lmin, lmax

    @Facet(units='nm', type=float)
    def wavelength(self):
        return Q_(self._device.getWavelength(NiceTLPM._defs['TLPM_ATTR_SET_VAL']))

    @wavelength.setter
    def wavelength(self, wavelength):
        self._device.setWavelength(wavelength)


if __name__ == '__main__':
    from instrumental import list_instruments, instrument

    psets = list_instruments(module='powermeters')
    with instrument(psets[0]) as powermeter:
        print(powermeter.get_device_info())
        print(powermeter.power_unit.name)
        powermeter.power_unit = 'W'
        print(powermeter.get_power())

        print(powermeter.get_wavelength_range())
        print(powermeter.wavelength)
        powermeter.wavelength = Q_('0.532µm')

