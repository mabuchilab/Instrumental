# -*- coding: utf-8 -*-
# Copyright 2013-2019 Nate Bogdanowicz
"""
Driver module for Santec Lasers.
"""
import datetime as dt
import time
import pyvisa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from enum import Enum

from . import Laser
from .. import VisaMixin, SCPI_Facet, Facet
from ..util import visa_context, check_enums, as_enum
from ...util import to_str
from ...errors import Error
from ... import u, Q_

class IsEnabled(Enum):
    Disabled = "0"
    Enabled = "1"

class WavelengthUnit(Enum):
    nm = "0"
    THz = "1"

class PowerUnit(Enum):
    dBm = "0"
    mW = "1"

class SweepMode(Enum):
    StepOneWay = "0"
    ContinuousOneWay = "1"
    StepTwoWay = "2"
    ContinuousTwoWay = "3"

class SweepSpeed(Enum):
    x1_nm_per_sec = "1"
    x2_nm_per_sec = "2"
    x5_nm_per_sec = "5"
    x10_nm_per_sec = "10"
    x20_nm_per_sec = "20"
    x50_nm_per_sec = "50"
    x100_nm_per_sec = "100"
    x200_nm_per_sec = "200"

class SweepState(Enum):
    Stopped = "0"
    Running = "1"
    Standby = "3"
    Preparation = "4"

class AmplitudeModulationSource(Enum):
    CoherenceControl = "0"
    IntensityModulation = "1"
    FrequencyModulation = "3"

class TriggerActiveLevel(Enum):
    High = "0"
    Low = "1"

class InputTriggerState(Enum):
    Normal = "0"
    Standby = "1"

class OutputTriggerMode(Enum):
    Unused = "0"  # "None" in the manual, can't use `None` as an Enum field in Python
    Stop = "1"
    Start = "2"
    Step = "3"

class TriggerStepMode(Enum):
    Time = "0"
    Wavelength = "1"

class SantecMessageFormat(Enum):
    Legacy = "0"
    SCPI = "1"

class MessageTermination(Enum):
    CR = "0"
    LF = "1"
    CR_LF = "2"
    Nothing = "3"

tsl570_command_errors = {
    0:      "No error",
    -102:   "Syntax error",
    -103:   "Invalid separator",
    -108:   "Parameter not allowed",
    -109:   "Missing parameter",
    -113:   "Undefined header",
    -148:   "Character data not allowed",
    -200:   "Execution error",
    -222:   "Data out of range",
    -410:   "Query INTERRUPTED",
}

### Santec TSL-570 System Alerts (manual page 100, sec. 7.4.6) ###

tsl570_system_alerts = {
    0:          "Power supply Error1",
    2:          "Power supply Error2",
    3:          "Power supply Error3",
    5:          "Wavelength Error",
    6:          "Power setting Error",
    7:          "Inter lock detection",
    20:         "Temperature control Error1",
    21:         "Temperature control Error2",
    22:         "Temperature control Error3",
    23:         "Ongoing Warm up",
    25:         "Shutter Error",
    26:         "Sensor Error",
    27:         "Connection Error",
    28:         "Exhaust Fan Error",
}

class TSL570(Laser, VisaMixin):
    """
    A class for Santec TSL-570 tunable laser.
    """

    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ("SANTEC",["TSL-570"])

    def _initialize(self):
        self.resource.write_termination    =   "\r"
        self.resource.read_termination     =   "\r"
        idn_resp = self.query("*IDN?")
        manufacturer, model, serial_number, firmware_version = idn_resp.split(",")
        self.manufacturer = manufacturer
        self.model = model
        self.serial_number = serial_number
        self.firmware_version = firmware_version
    
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
        self.communication_format = SantecMessageFormat.Legacy

    ### Santec TSL-570 Facets ###

    output_wavelength = SCPI_Facet(
        "WAVelength",
        type=        float,
        units=        "nm",
        doc=  "Sets the output wavelength. (manual page 69)",
        readonly=    False,
    ) 
    wavelength_units = SCPI_Facet(
        "WAVelength:UNIT",
        type=         WavelengthUnit,
        value=       {i: i.value for i in WavelengthUnit},
        doc=  "Sets units of displayed wavelength. (manual page 70)",
        readonly=    False,
    )  
    wavelength_fine_tuning = SCPI_Facet(
        "WAVelength:FINe",
        type=         float,
        limits=       [-100.0,100.0,0.01],
        doc=  "Sets Fine-Tuning value. (manual page 70)",
        readonly=    False,
    )    
    optical_frequency = SCPI_Facet(
        "FREQuency",
        type=         float,
        units=        "THz",
        doc=  "Sets the output optical frequency. (manual page 71)",
        readonly=    False,
    )  
    coherence_control = SCPI_Facet(
        "COHCtrl",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Sets Coherence control status. (manual page 72)",
        readonly=    False,
    )  
    output_on = SCPI_Facet(
        "POWer:STATe",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Sets optical output status. (manual page 72)",
        readonly=    False,
    )  
    output_attenuation = SCPI_Facet(
        "POWer:ATTenuation",
        type=         float,
        units=        "decibel",
        limits=       [0.0,30.0,0.01],
        doc=  "Sets the attenuator value. (manual page 73)",
        readonly=    False,
    )  
    auto_attenuation = SCPI_Facet(
        "POWer:ATTenuation:AUTo",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Sets the power control mode. (manual page 73)",
        readonly=    False,
    )  
    power_setpoint = SCPI_Facet(
        "POWer",
        type=         float,
        units=        "dBm", # "self.power_unit",
        limits=       [-15.0,20.0,0.01],
        doc=  "Sets optical output power level set point. (manual page 74)",
        readonly=    False,
    )
    power_measured = SCPI_Facet(
        "POWer:actual",
        type=         float,
        units=        "dBm", # "self.power_unit",
        doc=  "Measured optical output power level. (manual page 74)",
        readonly=    True,
    )  
    shutter = SCPI_Facet(
        "POWer:SHUTter",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Sets Open/Close status of the internal shutter. (manual page 75)",
        readonly=    False,
    )  
    power_unit = SCPI_Facet(
        "POWer:UNIT",
        type =       PowerUnit,
        value=       {PowerUnit.dBm:"0", PowerUnit.mW:"1"},
        doc=  "Changes the unit of the power setting and display. (manual page 76)",
        readonly=    False,
    )  
    sweep_start_wavelength = SCPI_Facet(
        "WAVelength:SWEep:STARt",
        type=         float,
        units=        "nm",
        doc=  "Sets the sweep start wavelength. (manual page 76)",
        readonly=    False,
    )  
    sweep_start_frequency = SCPI_Facet(
        "FREQuency:SWEep:STARt",
        type=         float,
        units=        "THz",
        doc=  "Sets the sweep start wavelength in optical frequency. (manual page 77)",
        readonly=    False,
    )  
    sweep_stop_wavelength = SCPI_Facet(
        "WAVelength:SWEep:STOP",
        type=         float,
        units=        "nm",
        doc=  "Sets the sweep stop wavelength. (manual page 78)",
        readonly=    False,
    )  
    sweep_stop_frequency = SCPI_Facet(
        "FREQuency:SWEep:STOP",
        type=         float,
        units=        "THz",
        doc=  "Sets the sweep stop wavelength in optical frequency. (manual page 79)",
        readonly=    False,
    )  
    sweep_mode = SCPI_Facet(
        "wavelength:sweep:mode",
        type=         SweepMode,
        value=       {i: i.value for i in SweepMode},
        doc=  "Sets the sweep mode. (manual page 80)",
        readonly=    False,
    )  
    sweep_speed = SCPI_Facet(
        "WAVelength:SWEep:SPEed",
        # units=        "nm/s",
        # value=        {1,2,5,10,20,50,100,200},
        type=        SweepSpeed,
        value=       {i: i.value for i in SweepSpeed},
        doc=  "Sets the sweep speed. (manual page 81)",
        readonly=    False,
    )  
    sweep_step_wavelength = SCPI_Facet(
        "WAVelength:SWEep:STEP",
        type=         float,
        units=        "nm",
        limits=       [0.0001,60.0,0.0001],
        doc=  "Sets the step for Step sweep mode. (manual page 81)",
        readonly=    False,
    )  
    sweep_step_frequency = SCPI_Facet(
        "FREQuency:SWEep:STEP",
        type=         float,
        units=        "THz",
        limits=       [0.00002,10.0,0.00001],
        doc=  "Sets the step for Step sweep mode in optical frequency. (manual page 82)",
        readonly=    False,
    )  
    sweep_dwell_time = SCPI_Facet(
        "WAVelength:SWEep:DWELl",
        type=         float,
        units=        "s",
        limits=       [0.0,999.9,0.1],
        doc=  "Sets wait time between consequent steps in step sweep mode. (manual page 83)",
        readonly=    False,
    )  
    sweep_num_cycles = SCPI_Facet(
        "WAVelength:SWEep:CYCLes",
        type=         int,
        limits=       [0,999,1],
        doc=  "Sets the sweep repetition times. (manual page 84)",
        readonly=    False,
    )
    sweep_cycle_count = SCPI_Facet(
        "WAVelength:SWEep:count",
        type=         int,
        limits=       [0,999,1],
        doc=  "Gets the number of times the sweep has been repeated so far. (manual page 84)",
        readonly=    True,
    )  
    sweep_delay_time = SCPI_Facet(
        "WAVelength:SWEep:DELay",
        type=         float,
        units=        "s",
        limits=       [0.0,999.9,0.1],
        doc=  "Sets the wait time between consequent scans. (manual page 85)",
        readonly=    False,
    )  
    sweep_state = SCPI_Facet(
        "WAVelength:SWEep:STATe",
        type=         SweepState,
        value=       {i: i.value for i in SweepState},
        doc=  "Sets sweep status and can be used to start a single sweep. (manual page 85)",
        readonly=    True,
    )  
    amplitude_modulation_enabled = SCPI_Facet(
        "AM:STATe",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Enables and disables modulation function of the laser output. (manual page 87)",
        readonly=    False,
    )  
    amplitude_modulation_source = SCPI_Facet(
        "AM:SOURce",
        type=         AmplitudeModulationSource,
        value=       {i: i.value for i in AmplitudeModulationSource},
        doc=  "Sets modulation source. (manual page 88)",
        readonly=    False,
    )  
    wavelength_offset = SCPI_Facet(
        "WAVelength:OFFSet",
        type=         float,
        units=        "nm",
        limits=       [-0.1,0.1,0.0001],
        doc=  "Add the constant offset to the output wavelength. (manual page 88)",
        readonly=    False,
    )  
    input_trigger_enable = SCPI_Facet(
        "TRIGger:INPut:EXTernal",
        type=         IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Enables / Disables external trigger input. (manual page 89)",
        readonly=    False,
    )  
    input_trigger_level = SCPI_Facet(
        "TRIGger:INPut:EXTernal:ACTive",
        type=         TriggerActiveLevel,
        value=       {i: i.value for i in TriggerActiveLevel},
        doc=  "Sets input trigger polarity. (manual page 90)",
        readonly=    False,
    )  
    input_trigger_passthrough = SCPI_Facet(
        "TRIGger:THRough",
        type=        IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Sets the trigger through mode. When True/On, input trigger signal is passed through to trigger output (manual page 93)",
        readonly=    False,
    ) 
    input_trigger_state = SCPI_Facet(
        "TRIGger:INPut:STANdby",
        type=        InputTriggerState,
        value=       {i: i.value for i in InputTriggerState},
        doc=  "Sets the device in trigger signal input standby mode. (manual page 90)",
        readonly=    False,
    ) 
    output_trigger_mode = SCPI_Facet(
        "TRIGger:OUTPut",
        type=        OutputTriggerMode,
        value=       {i: i.value for i in OutputTriggerMode},
        doc=  "Sets the timing of the trigger signal output. (manual page 91)",
        readonly=    False,
    )  
    output_trigger_level = SCPI_Facet(
        "TRIGger:OUTPut:ACTive",
        type=        TriggerActiveLevel,
        value=       {i: i.value for i in TriggerActiveLevel},
        doc=  "Sets output trigger active level (high or low). (manual page 91)",
        readonly=    False,
    )  
    output_trigger_step = SCPI_Facet(
        "TRIGger:OUTPut:STEP",
        type=         float,
        units=        "nm",
        limits=       [0.0001,60.0,0.0001],
        doc=  "Sets the interval of the trigger signal output. (manual page 92)",
        readonly=    False,
    )  
    output_trigger_step_type = SCPI_Facet(
        "TRIGger:OUTPut:SETTing",
        type=        TriggerStepMode,
        value=       {i: i.value for i in TriggerStepMode},
        doc=  "Sets the output trigger period mode. (manual page 93)",
        readonly=    False,
    )   
    system_error = SCPI_Facet(
        "SYSTem:error",
        type=        str,
        doc=  "Reads most recent system error. (manual page 94)",
        readonly=    True,
    )
    gpib_address = SCPI_Facet(
        "SYSTem:COMMunicate:GPIB:ADDRess",
        type=        int,
        limits=      [1,30,1],
        doc=  "Sets the GPIB address. (manual page 94)",
        readonly=    False,
    )  
    gpib_delimiter = SCPI_Facet(
        "SYSTem:COMMunicate:GPIB:DELimiter",
        # type=        int,
        value=       {"\r":"0", "\n":"1", "\r\n":"2", "":"3",},
        doc=  "Sets the command delimiter for GPIB communication. (manual page 95)",
        readonly=    False,
    )  
    mac_address = SCPI_Facet(
        "SYSTem:COMMunicate:ETHernet:macaddress",
        type=         str,
        doc=  "Reads out the MAC address of the laser's ethernet port. (manual page 95)",
        readonly=    True,
    )  
    ip_address = SCPI_Facet(
        "SYSTem:COMMunicate:ETHernet:IPADdress",
        type=         str,
        doc=  "Sets the laser's IP address in IPv4 format. (manual page 95)",
        readonly=    False,
    )  
    ip_subnet_mask = SCPI_Facet(
        "SYSTem:COMMunicate:ETHernet:SMASk",
        type=         str,
        doc=  "Sets the subnet mask in IPv4 format. (manual page 96)",
        readonly=    False,
    )  
    ip_default_gateway = SCPI_Facet(
        "SYSTem:COMMunicate:ETHernet:DGATeway",
        type=         str,
        doc=  "Sets the default gateway in IPv4 format. (manual page 96)",
        readonly=    False,
    )  
    ip_port = SCPI_Facet(
        "SYSTem:COMMunicate:ETHernet:PORT",
        type=         int,
        limits=       [0,65535,1],
        doc=  "Sets the port number used for TCP/IP communication via the laser's ethernet port. (manual page 97)",
        readonly=    False,
    )  
    communication_format = SCPI_Facet(
        "SYSTem:COMMunicate:CODe",
        # # type=         int,
        # value=       {"Legacy":"0", "SCPI":"1",},
        type=        SantecMessageFormat,
        value=       {i: i.value for i in SantecMessageFormat},
        doc=  "Sets the command set. (manual page 97)",
        readonly=    False,
    )
    external_interlock = SCPI_Facet(
        "system:lock",
        type=        IsEnabled,
        value=       {i: i.value for i in IsEnabled},
        doc=  "Reads out the status of the laser's external interlock. (manual page 98)",
        readonly=    True,
    )    
    display_brightness = SCPI_Facet(
        "DISPlay:BRIGhtness",
        type=         int,
        limits=       [0,100,1],
        doc=  "Sets brightness of the display (in %). (manual page 98)",
        readonly=    False,
    )
    system_alert = SCPI_Facet(
        "SYSTem:alert",
        type=        str,
        doc=  "Reads most recent system alert. (manual page 99)",
        readonly=    True,
    )
    num_log_points = SCPI_Facet(
        "READOUT:POINTS",
        type=        int,
        doc=  "Checks how many log data points are available to be read out. (manual page 86)",
        readonly=    True,
    )

    ### TSL-570 Commands

    def disable_wavelength_fine_tuning(self):
        """Terminate Fine-Tuning operation. (manual page 71)"""
        self.write("WAVelength:FINetuning:DISable")

    def start_repeating_sweep(self):
        """Start repeat wavelength sweep. (manual page 86)"""
        self.write("WAVelength:SWEep:STATe:REPeat")
    
    def software_trigger(self):
        """Execute sweep from trigger standby mode. (manual page 91)"""
        self.write("TRIGger:INPut:SOFTtrigger")
    
    def shutdown(self):
        """Shutdown TSL-570 laser. (manual page 98)"""
        self.write("SPECial:SHUTdown")

    def reboot(self):
        """Reboot TSL-570 laser. (manual page 98)"""
        self.write("SPECial:reboot")

    def _read_data(
            self,
            query_string='READOUT:DATA?',
            # bytes_per_sample=8, # 64-bit format
            # dtype='float64',
            bytes_per_sample=4, # 32-bit format
            dtype='int32',
    ):

        with self.resource.ignore_warning(pyvisa.constants.VI_SUCCESS_MAX_CNT),\
            visa_context(self.resource, timeout=10000, read_termination=None,
                         end_input=pyvisa.constants.SerialTermination.none):

            self.write(query_string)
            visalib = self.resource.visalib
            session = self.resource.session

            # NB: Must take slice of bytes returned by visalib.read,
            # to keep from autoconverting to int
            width_byte = visalib.read(session, 2)[0][1:]  # read first 2 bytes
            num_bytes = int(visalib.read(session, int(width_byte))[0])
            buf = bytearray(num_bytes)
            cursor = 0

            while cursor < num_bytes:
                raw_bin, _ = visalib.read(session, num_bytes-cursor)
                buf[cursor:cursor+len(raw_bin)] = raw_bin
                cursor += len(raw_bin)

        # self.resource.read()  # Eat termination

        num_points = int(num_bytes // bytes_per_sample)
        # dtype = '>i{:d}'.format(bytes_per_sample)
        log_data = np.frombuffer(buf, dtype=dtype, count=num_points)
        return log_data

    def read_wavelength_data(self,bytes_per_sample=4,dtype='int32',data_step=0.1*u.pm):
        wavelength_data_raw = self._read_data(
                query_string='READOUT:DATA?',
                bytes_per_sample=bytes_per_sample,
                dtype=dtype,
        )
        wavelength_data = (wavelength_data_raw*data_step).to('nm')
        return wavelength_data

    def read_power_data(self,bytes_per_sample=4,dtype='float32',data_step=Q_(1.0,"dBm")):
        power_data_raw = self._read_data(
                query_string='READOUT:DATA:POWER?',
                bytes_per_sample=bytes_per_sample,
                dtype=dtype,
        )
        # power_data = (power_data_raw*data_step).to('dBm')
        power_data = power_data_raw*data_step
        return power_data

    def configure_continuous_sweep(
        self,
        sweep_start,
        sweep_stop,
        sweep_speed:SweepSpeed = SweepSpeed.x10_nm_per_sec,
        sweep_mode:SweepMode = SweepMode.ContinuousOneWay,
        sweep_dwell_time = 0.0 * u.second,
        sweep_num_cycles = 1,
        sweep_delay_time = 0.0 * u.second,
        input_trigger_enable = IsEnabled.Enabled,
        input_trigger_level = TriggerActiveLevel.High,
        # input_trigger_state = InputTriggerState.Normal,
        output_trigger_mode = OutputTriggerMode.Step,
        output_trigger_level = TriggerActiveLevel.High,
        output_trigger_step = 10 * u.pm,
        output_trigger_step_type = TriggerStepMode.Time,
        sleep_time=0.01*u.second,
    ):
        # Normalize units of start and stop wavelengths/frequencies, accepting either type of data
        self.sweep_start_wavelength      =   sweep_start.to(u.nm,"sp")
        self.sweep_stop_wavelength       =   sweep_stop.to(u.nm,"sp")

        # Assign Facet values
        self.sweep_speed                 =   sweep_speed
        self.sweep_mode                  =   sweep_mode
        self.sweep_dwell_time            =   sweep_dwell_time
        self.sweep_num_cycles            =   sweep_num_cycles
        self.sweep_delay_time            =   sweep_delay_time
        self.input_trigger_enable        =   input_trigger_enable
        self.input_trigger_level         =   input_trigger_level
        # self.input_trigger_state         =   input_trigger_state
        self.output_trigger_mode         =   output_trigger_mode
        self.output_trigger_level        =   output_trigger_level
        self.output_trigger_step         =   output_trigger_step
        self.output_trigger_step_type    =   output_trigger_step_type
        
        # while self.sweep_cycle_count < self.sweep_num_cycles:

    def wait_until_operation_complete(self,sleep_time=0.01*u.second):
        opc = 0
        while opc  == 0:
            time.sleep(sleep_time.m_as(u.second))
            opc = self.query('*OPC?')

    def arm_input_trigger(self,sleep_time=0.01*u.second):
        self.input_trigger_state = InputTriggerState.Standby
        trigger_armed = False
        while not(trigger_armed):
            time.sleep(sleep_time.m_as(u.second))
            if self.input_trigger_state is InputTriggerState.Standby:
                trigger_armed = True

    def start_sweep(self,sleep_time=0.01*u.second):
        if self.output_wavelength != self.sweep_start_wavelength:
            self.output_wavelength = self.sweep_start_wavelength
        self.wait_until_operation_complete(sleep_time=sleep_time)
        # if self.input_trigger_enable:
        #     self.arm_input_trigger(sleep_time=sleep_time)
        if self.input_trigger_enable:
            self.arm_input_trigger(sleep_time=sleep_time)
            self.write("WAVelength:SWEep:STATe 1")
        else:
            self.arm_input_trigger(sleep_time=sleep_time)
            self.write("WAVelength:SWEep:STATe 1")
            self.software_trigger()
        
    def run_sweep(self,sleep_time=0.01*u.second):
        self.start_sweep(sleep_time=sleep_time)
        while self.sweep_state in [SweepState.Preparation,SweepState.Running]:
            time.sleep(sleep_time.m_as(u.second))
        wavelength_data = self.read_wavelength_data()
        power_data = self.read_power_data()
        return wavelength_data, power_data


    # def get_data(self, width=2, bounds=None):
    #     """Retrieve wavelength, frequency or power values from the laser corresponding to trigger events or step values in the last sweep.

    #     Pulls data from channel `channel` and returns it as a tuple ``(t,y)``
    #     of unitful arrays.

    #     Parameters
    #     ----------
    #     channel : int, optional
    #         Channel number to pull trace from. Defaults to channel 1.
    #     width : int, optional
    #         Number of bytes per sample of data pulled from the scope. 1 or 2.
    #     bounds : tuple of int, optional
    #         (start, stop) tuple of first and last sample to read. Index starts at 1.

    #     Returns
    #     -------
    #     t, y : pint.Quantity arrays
    #         Unitful arrays of data from the scope. ``t`` is in seconds, while
    #         ``y`` is in volts.
    #     """
    #     if width not in (1, 2):
    #         raise ValueError('width must be 1 or 2')

    #     with self.transaction():
    #         self.write("data:source ch{}".format(channel))
    #         self.write("data:width {}", width)
    #         self.write("data:encdg RIBinary")

    #     if bounds is None:
    #         start = 1
    #         # scope *should* truncate this to record length if it's too big
    #         stop = getattr(self, 'max_waveform_length', 1000000)
    #     else:
    #         start, stop = bounds
    #         wfm_len = self.waveform_length
    #         if not (1 <= start <= stop <= wfm_len):
    #             raise ValueError('bounds must satisfy 1 <= start <= stop <= {}'.format(wfm_len))

    #     with self.transaction():
    #         self.write("data:start {}".format(start))
    #         self.write("data:stop {}".format(stop))

    #     #self.resource.flow_control = 1  # Soft flagging (XON/XOFF flow control)
    #     raw_data_y = self._read_curve(width=width)
    #     raw_data_x = np.arange(1, len(raw_data_y)+1)

    #     # Get scale and offset factors
    #     wp = self._waveform_params()
    #     x_units = self._tek_units(wp['xun'])
    #     y_units = self._tek_units(wp['yun'])

    #     data_x = Q_((raw_data_x - wp['pt_o'])*wp['xin'] + wp['xze'], x_units)
    #     data_y = Q_((raw_data_y - wp['yof'])*wp['ymu'] + wp['yze'], y_units)

    #     return data_x, data_y

    # @staticmethod
    # def _tek_units(unit_str):
    #     unit_map = {
    #         'U': '',
    #         'Volts': 'V'
    #     }

    #     unit_str = unit_map.get(unit_str, unit_str)
    #     try:
    #         units = u.parse_units(unit_str)
    #     except UndefinedUnitError:
    #         units = u.dimensionless
    #     return units

    # def _read_curve(self, width):
    #     with self.resource.ignore_warning(pyvisa.constants.VI_SUCCESS_MAX_CNT),\
    #         visa_context(self.resource, timeout=10000, read_termination=None,
    #                      end_input=pyvisa.constants.SerialTermination.none):

    #         self.write("curve?")
    #         visalib = self.resource.visalib
    #         session = self.resource.session

    #         # NB: Must take slice of bytes returned by visalib.read,
    #         # to keep from autoconverting to int
    #         width_byte = visalib.read(session, 2)[0][1:]  # read first 2 bytes
    #         num_bytes = int(visalib.read(session, int(width_byte))[0])
    #         buf = bytearray(num_bytes)
    #         cursor = 0

    #         while cursor < num_bytes:
    #             raw_bin, _ = visalib.read(session, num_bytes-cursor)
    #             buf[cursor:cursor+len(raw_bin)] = raw_bin
    #             cursor += len(raw_bin)

    #     self.resource.read()  # Eat termination

    #     num_points = int(num_bytes // width)
    #     dtype = '>i{:d}'.format(width)
    #     return np.frombuffer(buf, dtype=dtype, count=num_points)

    # def run_acquire(self):
    #     """Sets the acquire state to 'run'"""
    #     self.write("acquire:state run")

    # def stop_acquire(self):
    #     """Sets the acquire state to 'stop'"""
    #     self.write("acquire:state stop")

    # @property
    # def interface_type(self):
    #     return self.resource.interface_type

    # @property
    # def model(self):
    #     _, model, _, _ = self.query('*IDN?').split(',', 3)
    #     return model

    # @property
    # def channels(self):
    #     try:
    #         return MODEL_CHANNELS[self.model]
    #     except KeyError:
    #         raise KeyError('Unknown number of channels for this scope model')

    # def read_events(self):
    #     """Get a list of events from the Event Queue

    #     Returns
    #     -------
    #     A list of (int, str) pairs containing the code and message for each event in the scope's
    #     event queue.
    #     """
    #     events = []
    #     while True:
    #         event_info = self.query('evmsg?').split(',', 1)
    #         code = int(event_info[0])
    #         message = event_info[1][1:-1]
    #         if code == 0:
    #             break
    #         elif code == 1:
    #             self.query('*ESR?')  # Reload event queue
    #         else:
    #             events.append((code, message))
    #     return events

    # @property
    # def _datetime(self):
    #     resp = self.query(':date?;:time?')
    #     return dt.datetime.strptime(resp, '"%Y-%m-%d";"%H:%M:%S"')

    # @_datetime.setter
    # def _datetime(self, value):
    #     if not isinstance(value, dt.datetime):
    #         raise TypeError('value must be a datetime object')
    #     message = value.strftime(':date "%Y-%m-%d";:time "%H:%M:%S"')
    #     self.write(message)

    # horizontal_scale = SCPI_Facet('hor:main:scale', convert=float, units='s')
    # horizontal_delay = SCPI_Facet('hor:delay:pos', convert=float, units='s')
    # math_function = property(get_math_function, set_math_function)
