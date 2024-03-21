# -*- coding: utf-8 -*-
# Copyright 2013-2023 Nate Bogdanowicz, Dodd Gray
"""
Driver module for Vescent Temperature Controllers.
"""
import datetime as dt
import time
import pyvisa as visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from enum import Enum

from . import TempController
from .. import VisaMixin, SCPI_Facet, Facet
from ..util import visa_context, check_enums, as_enum
from ...util import to_str
from ...errors import Error
from ... import u, Q_

class SliceQTC(TempController, VisaMixin):
    """
    A class for Vescent Slice-QTC 4-Channel Temperature Controllers.

    Product Website:    https://vescent.com/us/slice-qtc-four-channel-temperature-controller.html

    API Documentation:  https://www.vescent.com/manuals/doku.php?id=slice:qt:api
    """

    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ("Vescent",["Slice-QTC"])

    def _initialize(self):
        self.resource.write_termination    =   "\r"
        self.resource.read_termination     =   "\r"
        idn_resp = self.query("*IDN?")
        # manufacturer, model, serial_number, firmware_version = idn_resp.split(",")
        # self.manufacturer = manufacturer
        # self.model = model
        # self.serial_number = serial_number
        # self.firmware_version = firmware_version

    #     if self.interface_type == InterfaceType.asrl:
    #         terminator = self.query('RS232:trans:term?').strip()
    #         self.resource.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
    #     elif self.interface_type == InterfaceType.usb:
    #         msg = self.query('*IDN?')
    #         self.resource.read_termination = infer_termination(msg)
    #     elif self.interface_type == InterfaceType.tcpip:
    #         msg = self.query('*IDN?')
    #         self.resource.write_termination    =   "\r"
    #         self.resource.read_termination     =   "\r"
    #     else:
    #         pass

        ### Set the TSL-570 communication format to Santec's "Legacy" style
        # self.write('SYST:COMM:COD 0') 

    ### Vescent Slice-QTC Facets ###

    # output_wavelength = SCPI_Facet(
    #     "WAVelength",
    #     type=        float,
    #     units=        "nm",
    #     doc=  "Sets the output wavelength. (manual page 69)",
    #     readonly=    False,
    # ) 
    # wavelength_units = SCPI_Facet(
    #     "WAVelength:UNIT",
    #     type=         WavelengthUnit,
    #     value=       {i: i.value for i in WavelengthUnit},
    #     doc=  "Sets units of displayed wavelength. (manual page 70)",
    #     readonly=    False,
    # )  