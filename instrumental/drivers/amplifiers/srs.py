# -*- coding: utf-8 -*-
# Copyright 2014-2017 Dodd Gray, Nate Bogdanowicz
"""
Driver for VISA control of Stanford Research Systems (SRS) SR570 Low-Noise
Current Preamplifier via RS-232 via Visa. Could Easily be adapted for control
of other SRS instruments. Note that the SR570 is a listen-only instrument,
meaning it cannot be identified automatically by the computer checking the
response of the instrument to a generic serial/Visa command like '*IDN?'.
"""

from __future__ import unicode_literals

from pyvisa.constants import Parity, StopBits
from enum import Enum
from . import Amplifier
from .. import VisaMixin, Facet
from ..util import visa_context
from ...log import get_logger
from ... import u, Q_
import numpy as np
from time import sleep
log = get_logger(__name__)

__all__ = ['SR570']

_INST_PARAMS = ['visa_address']
_INST_CLASSES = ['SR570']


# SR570 Message Enums
#
class SR570_Sensitivity(Enum):
    s_1pA_V = 'SENS 0'
    s_2pA_V = 'SENS 1'
    s_5pA_V = 'SENS 2'
    s_10pA_V = 'SENS 3'
    s_20pA_V = 'SENS 4'
    s_50pA_V = 'SENS 5'
    s_100pA_V = 'SENS 6'
    s_200pA_V = 'SENS 7'
    s_500pA_V = 'SENS 8'
    s_1nA_V = 'SENS 9'
    s_2nA_V = 'SENS 10'
    s_5nA_V = 'SENS 11'
    s_10nA_V = 'SENS 12'
    s_20nA_V = 'SENS 13'
    s_50nA_V = 'SENS 14'
    s_100nA_V = 'SENS 15'
    s_200nA_V = 'SENS 16'
    s_500nA_V = 'SENS 17'
    s_1uA_V = 'SENS 18'
    s_2uA_V = 'SENS 19'
    s_5uA_V = 'SENS 20'
    s_10uA_V = 'SENS 21'
    s_20uA_V = 'SENS 22'
    s_50uA_V = 'SENS 23'
    s_100uA_V = 'SENS 24'
    s_200uA_V = 'SENS 25'
    s_500uA_V = 'SENS 26'
    s_1mA_V = 'SENS 27'

class SR570_OffsetCurrentLevel(Enum):
    io_1pA = 'IOLV 0'
    io_2pA = 'IOLV 1'
    io_5pA = 'IOLV 2'
    io_10pA = 'IOLV 3'
    io_20pA = 'IOLV 4'
    io_50pA = 'IOLV 5'
    io_100pA = 'IOLV 6'
    io_200pA = 'IOLV 7'
    io_500pA = 'IOLV 8'
    io_1nA = 'IOLV 9'
    io_2nA = 'IOLV 10'
    io_5nA = 'IOLV 11'
    io_10nA = 'IOLV 12'
    io_20nA = 'IOLV 13'
    io_50nA = 'IOLV 14'
    io_100nA = 'IOLV 15'
    io_200nA = 'IOLV 16'
    io_500nA = 'IOLV 17'
    io_1uA = 'IOLV 18'
    io_2uA = 'IOLV 19'
    io_5uA = 'IOLV 20'
    io_10uA = 'IOLV 21'
    io_20uA = 'IOLV 22'
    io_50uA = 'IOLV 23'
    io_100uA = 'IOLV 24'
    io_200uA = 'IOLV 25'
    io_500uA = 'IOLV 26'
    io_1mA = 'IOLV 27'
    io_2mA = 'IOLV 28'
    io_5mA = 'IOLV 29'

class SR570_InputOffsetCurrentToggle(Enum):
    on = 'IOON 1'
    off = 'IOON 0'

class SR570_InputOffsetCurrentSign(Enum):
    positive = 'IOSN 1'
    negative = 'IOSN 0'


class SR570_HighPassFrequency(Enum):
    hf_30mHz = 'HFRQ 0'
    hf_100mHz = 'HFRQ 1'
    hf_300mHz = 'HFRQ 2'
    hf_1Hz = 'HFRQ 3'
    hf_3Hz = 'HFRQ 4'
    hf_10Hz = 'HFRQ 5'
    hf_30Hz = 'HFRQ 6'
    hf_100Hz = 'HFRQ 7'
    hf_300Hz = 'HFRQ 8'
    hf_1kHz = 'HFRQ 9'
    hf_3kHz = 'HFRQ 10'
    hf_10kHz = 'HFRQ 11'


class SR570_LowPassFrequency(Enum):
    lf_30mHz = 'LFRQ 0'
    lf_100mHz = 'LFRQ 1'
    lf_300mHz = 'LFRQ 2'
    lf_1Hz = 'LFRQ 3'
    lf_3Hz = 'LFRQ 4'
    lf_10Hz = 'LFRQ 5'
    lf_30Hz = 'LFRQ 6'
    lf_100Hz = 'LFRQ 7'
    lf_300Hz = 'LFRQ 8'
    lf_1kHz = 'LFRQ 9'
    lf_3kHz = 'LFRQ 10'
    lf_10kHz = 'LFRQ 11'
    lf_30kHz = 'LFRQ 12'
    lf_100kHz = 'LFRQ 13'
    lf_300kHz = 'LFRQ 14'
    lf_1MHz = 'LFRQ 15'

class SR570_Filter(Enum):
    hp_6dB = 'FLTT 0'
    hp_12dB = 'FLTT 1'
    bp_6dB = 'FLTT 2'
    lp_6dB = 'FLTT 3'
    lp_12dB = 'FLTT 4'
    none = 'FLTT 5'

class SR570_BiasVoltageToggle(Enum):
    on = 'BSON 1'
    off = 'BSON 0'

class SR570_InvertToggle(Enum):
    on = 'INVT 1'
    off = 'INVT 0'

class SR570_BlankToggle(Enum):
    on = 'BLNK 1'
    off = 'BLNK 0'

class SR570_GainMode(Enum):
    low_noise = 'GNMD 0'
    high_bandwidth = 'GNMD 1'
    low_drift = 'GNMD 2'

class SR570(Amplifier, VisaMixin):
    """
    Stanford Research Systems (SRS) SR570 Low-Noise Current Preamplifier.
    Note that the SR570 is a listen-only instrument, meaning it cannot be
    identified automatically by the computer checking the response of the
    instrument to a generic serial/Visa command like '*IDN?'.

    So that the python SR570 object can keep track of the state of the
    amplifier, the amplifier will always be initialized into the
    "default state", defined in the manual to be:

    Sensitivity = 1 µA/V, calibrated
    Invert = off
    Input Offset = +1 pA, calibrated, off
    Bias = 0 V, off
    Filters = none
    Highpass Freq = 0.03 Hz
    Lowpass Freq = 1 MHz
    Gain Mode = Low Noise
    """

    def _initialize(self):
        self._rsrc.parity = Parity.none
        self._rsrc.write_termination = '\r\n'
        self._rsrc.stop_bits = StopBits.two
        self.reset_config()
        self.sensitivity = 1 * u.uA / u.volt
        self.invert = False
        self.blank = False
        self.bias_voltage_on = False
        self.bias_voltage = 0*u.volt
        self.input_offset_current_sign = SR570_InputOffsetCurrentSign.positive
        self.input_offset_current = 1 * u.pA
        self.input_offset_current = False
        self.hp_frequency = 30 * u.mHz
        self.lp_frequency = 1 * u.MHz
        self.gain_mode = SR570_GainMode.low_noise
        self.sensitivity_levels = np.array([1e-12,2e-12,5e-12,
                                    10e-12,20e-12,50e-12,
                                    100e-12,200e-12,500e-12,
                                    1e-9,2e-9,5e-9,
                                    10e-9,20e-9,50e-9,
                                    100e-9,200e-9,500e-9,
                                    1e-6,2e-6,5e-6,
                                    10e-6,20e-6,50e-6,
                                    100e-6,200e-6,500e-6,
                                    1e-3])*u.ampere/u.volt
        self.offset_current_levels = np.array([1e-12,2e-12,5e-12,
                                    10e-12,20e-12,50e-12,
                                    100e-12,200e-12,500e-12,
                                    1e-9,2e-9,5e-9,
                                    10e-9,20e-9,50e-9,
                                    100e-9,200e-9,500e-9,
                                    1e-6,2e-6,5e-6,
                                    10e-6,20e-6,50e-6,
                                    100e-6,200e-6,500e-6,
                                    1e-3,2e-3,5e-3])*u.ampere
        self.frequencies = np.array([30e-3,
                                    100e-3, 300e-3,
                                    1, 3,
                                    10, 30,
                                    100, 300,
                                    1e3, 3e3,
                                    10e3, 30e3,
                                    100e3, 300e3,
                                    1e6 ]) * u.Hz
        self.hpf_keys = [member for member in SR570_HighPassFrequency.__members__]
        self.lpf_keys = [member for member in SR570_LowPassFrequency.__members__]
        self.sensitivity_keys = [member for member in SR570_Sensitivity.__members__]
        self.offset_current_level_keys = [member for member in SR570_OffsetCurrentLevel.__members__]


    def reset_config(self):
        """
        Send command to SR570 to default settings
        """
        self._rsrc.write('*RST')

    def reset_filters(self):
        """
        Send command to SR570 to dump capacitors in analog filters, resetting
        their state after an overload condition.
        """
        self._rsrc.write('ROLD')

    def set_sensitivity(self,sensitivity):
        sensitivity_ind = [i for i, lvl in enumerate(sensitivity-self.sensitivity_levels <= 0.0*sensitivity.units) if lvl][0]
        self._rsrc.write(SR570_Sensitivity[self.sensitivity_keys[sensitivity_ind]].value)
        self.sensitivity = self.sensitivity_levels[sensitivity_ind]
        return self.sensitivity

    def set_offset_current(self,offset_current):
        oc_level_ind = [i for i, lvl in enumerate(abs(offset_current)-self.offset_current_levels <= offset_current.units) if lvl][0]
        if offset_current < (0 * u.ampere):
            self._rsrc.write(SR570_InputOffsetCurrentSign.negative.value)
            self.offset_current = -1 * self.offset_current_levels[oc_level_ind]
        else:
            self._rsrc.write(SR570_InputOffsetCurrentSign.positive.value)
            self.offset_current = self.offset_current_levels[oc_level_ind]
        sleep(0.2) # allow time for SR570 to react to first request
        self._rsrc.write(SR570_OffsetCurrentLevel[self.offset_current_level_keys[oc_level_ind]].value)
        return self.offset_current

    def set_hp_frequency(self,frequency):
        if frequency >= self.lp_frequency:
            raise Exception('attempt to set SR570 highpass frequency to {:1.1g} Hz, which is >= current lowpass frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.lp_frequency.to(u.Hz).m))
        else:
            hp_freq_ind = [i for i, f in enumerate(frequency-self.frequencies[:12] >= 0.0*frequency.units) if not(f)][0] - 1 # restrict max HP frequency setting to 10kHz
            #high_freq_ind = [i for i, f in enumerate(frequency-self.frequencies <= 0.0 * frequency.units) if f][0]
            print(SR570_HighPassFrequency[self.hpf_keys[hp_freq_ind]].value)
            self._rsrc.write(SR570_HighPassFrequency[self.hpf_keys[hp_freq_ind]].value)
            self.hp_frequency = self.frequencies[hp_freq_ind]
        return self.hp_frequency

    def set_lp_frequency(self,frequency):
        if frequency <= self.hp_frequency:
            raise Exception('attempt to set SR570 lowpass frequency to {:1.1g} Hz, which is <= current highpass frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.hp_frequency.to(u.Hz).m))
        else:
            lp_freq_ind = [i for i, f in enumerate(frequency-self.frequencies <= 0.0 * frequency.units) if f][0]
            #low_freq_ind = [i for i, f in enumerate(frequency-self.frequencies >= 0.0*frequency.units) if not(f)][0] - 1
            print(SR570_LowPassFrequency[self.lpf_keys[lp_freq_ind]].value)
            self._rsrc.write(SR570_LowPassFrequency[self.lpf_keys[lp_freq_ind]].value)
            self.lp_frequency = self.frequencies[lp_freq_ind]
        return self.lp_frequency

    def set_filter_type(self,filter_type):
        try:
            self._rsrc.write(SR570_Filter[filter_type].value)
            self.filter_type = SR570_Filter[filter_type]
        except:
            raise Exception('Unrecognized SR570 filter type: ' + str(filter_type))

    def set_gain_mode(self,gain_mode):
        try:
            self._rsrc.write(SR570_GainMode[gain_mode].value)
            self.gain_mode = SR570_GainMode[gain_mode]
        except:
            raise Exception('Unrecognized SR570 gain_mode: ' + str(gain_mode))

    def offset_current_on(self):
        self._rsrc.write(SR570_InputOffsetCurrentToggle.on.value)
        self.input_offset_current = True

    def offset_current_off(self):
        self._rsrc.write(SR570_InputOffsetCurrentToggle.off.value)
        self.input_offset_current = False

    def blank_on(self):
        self._rsrc.write(SR570_BlankToggle.on.value)
        self.blank = True

    def blank_off(self):
        self._rsrc.write(SR570_BlankToggle.off.value)
        self.blank = False

    def invert_on(self):
        self._rsrc.write(SR570_InvertToggle.on.value)
        self.invert = True

    def invert_off(self):
        self._rsrc.write(SR570_InvertToggle.off.value)
        self.invert = False

    def set_bias_voltage_on(self):
        self._rsrc.write(SR570_BiasVoltageToggle.on.value)
        self.bias_voltage_on = True

    def set_bias_voltage_off(self):
        self._rsrc.write(SR570_Bias_voltageToggle.off.value)
        self.bias_voltage_on = False

    def set_bias_voltage(self,V_set):
        self._rsrc.write("BSLV {}".format(int(round(V_set.to(u.millivolt).m))))
        self.bias_voltage = True

# SR560 Message Enums
#
class SR560_Gain(Enum):
    g_1 = 'GAIN 0'
    g_2 = 'GAIN 1'
    g_5 = 'GAIN 2'
    g_10 = 'GAIN 3'
    g_20 = 'GAIN 4'
    g_50 = 'GAIN 5'
    g_100 = 'GAIN 6'
    g_200 = 'GAIN 7'
    g_500 = 'GAIN 8'
    g_1k = 'GAIN 9'
    g_2k = 'GAIN 10'
    g_5k = 'GAIN 11'
    g_10k = 'GAIN 12'
    g_20k = 'GAIN 13'
    g_50k = 'GAIN 14'

class SR560_HighPassFrequency(Enum):
    hf_30mHz = 'HFRQ 0'
    hf_100mHz = 'HFRQ 1'
    hf_300mHz = 'HFRQ 2'
    hf_1Hz = 'HFRQ 3'
    hf_3Hz = 'HFRQ 4'
    hf_10Hz = 'HFRQ 5'
    hf_30Hz = 'HFRQ 6'
    hf_100Hz = 'HFRQ 7'
    hf_300Hz = 'HFRQ 8'
    hf_1kHz = 'HFRQ 9'
    hf_3kHz = 'HFRQ 10'
    hf_10kHz = 'HFRQ 11'


class SR560_LowPassFrequency(Enum):
    lf_30mHz = 'LFRQ 0'
    lf_100mHz = 'LFRQ 1'
    lf_300mHz = 'LFRQ 2'
    lf_1Hz = 'LFRQ 3'
    lf_3Hz = 'LFRQ 4'
    lf_10Hz = 'LFRQ 5'
    lf_30Hz = 'LFRQ 6'
    lf_100Hz = 'LFRQ 7'
    lf_300Hz = 'LFRQ 8'
    lf_1kHz = 'LFRQ 9'
    lf_3kHz = 'LFRQ 10'
    lf_10kHz = 'LFRQ 11'
    lf_30kHz = 'LFRQ 12'
    lf_100kHz = 'LFRQ 13'
    lf_300kHz = 'LFRQ 14'
    lf_1MHz = 'LFRQ 15'

class SR560_GainMode(Enum):
    low_noise = 'DYNR 0'
    high_dynamic_reserve = 'DYNR 1'
    calibration_gains = 'DYNR 2'
 # I don't understand this, manual says default is "calibration gains"
 # on page A-1, but earlier on page 3 it says the default is high dynamic range,
 # and then ours ges into "low noise" when reset...

class SR560_Filter(Enum):
    hp_6dB = 'FLTM 3'
    hp_12dB = 'FLTM 4'
    bp_6dB = 'FLTM 5'
    lp_6dB = 'FLTM 1'
    lp_12dB = 'FLTM 2'
    none = 'FLTM 0'
    bypass = 'FLTM 0'

class SR560_InvertToggle(Enum):
    on = 'INVT 1'
    off = 'INVT 0'

class SR560_Source(Enum):
    ChA = 'SRCE 0'
    ChAminusChB = 'SRCE 1'
    ChB = 'SRCE 2'

class SR560_Coupling(Enum):
    ground = 'CPLG 0'
    DC = 'CPLG 1'
    AC = 'CPLG 2'

class SR560_BlankToggle(Enum):
    on = 'BLNK 1'
    off = 'BLNK 0'
    # another weird thing about the manual-
    # it says command for blanking is "BLINK"
    # maybe a typo?

class SR560(Amplifier, VisaMixin):
    """
    Stanford Research Systems (SRS) SR560 Low-Noise (Voltage) Preamplifier.
    Note that the SR560 is a listen-only instrument, meaning it cannot be
    identified automatically by the computer checking the response of the
    instrument to a generic serial/Visa command like '*IDN?'.

    Note that SR560's can be hardware configured (with switches on the back)
    so that up to four are independently addressable with the commands wrapped
    in this driver while connected to the same serial line. This is not
    implemented in this driver yet, but would be easy to add, just by
    giving each instantiated SR560 an address i (1-4) and calling 'LISN i'
    before each command rather than 'LALL', which calls all SR560s on the line.

    So that the python SR560 object can keep track of the state of the
    amplifier, the amplifier will always be initialized into the
    "default state", defined in the manual to be:

    Source: Channel A
    Gain: 20
    Coupling: DC
    Invert = off
    Rolloff: bypassed
    High-pass: 0.03 Hz, +6 dB/oct
    High-pass: 1MHz, -6 dB/oct
    Listen: on
    """

    def _initialize(self):
        self._rsrc.parity = Parity.none
        self._rsrc.write_termination = '\r\n'
        self._rsrc.stop_bits = StopBits.two
        self.t_sleep = 0.1 # seconds, wait time between successive commands
        self.reset_config()
        self.gain = 20
        self.invert = False
        self.blank = False
        self.filter_type =  SR560_Filter.none
        self.hp_frequency = 30 * u.mHz
        self.lp_frequency = 1 * u.MHz
        self.gain_mode = SR560_GainMode.low_noise
        self.source = SR560_Source.ChA
        self.coupling = SR560_Coupling.DC
        self.gain_levels = np.array([1,2,5,
                                    10,20,50,
                                    100,200,500,
                                    1e3,2e3,5e3,
                                    10e3,20e3,50e3])
        self.frequencies = np.array([30e-3,
                                    100e-3, 300e-3,
                                    1, 3,
                                    10, 30,
                                    100, 300,
                                    1e3, 3e3,
                                    10e3, 30e3,
                                    100e3, 300e3,
                                    1e6 ]) * u.Hz
        self.hpf_keys = [member for member in SR560_HighPassFrequency.__members__]
        self.lpf_keys = [member for member in SR560_LowPassFrequency.__members__]
        self.gain_keys = [member for member in SR560_Gain.__members__]


    def reset_config(self):
        """
        Send command to SR560 to default settings
        """
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write('*RST')
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')

    def reset_filters(self):
        """
        Send command to SR560 to dump capacitors in analog filters, resetting
        their state after an overload condition. Note, the reset takes 1/2 second.
        """
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write('ROLD')
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')

    def set_gain(self,gain):
        gain_ind = [i for i, lvl in enumerate(gain-self.gain_levels <= 0.0) if lvl][0]
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write(SR560_Gain[self.gain_keys[gain_ind]].value)
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')
        self.gain = self.gain_levels[gain_ind]
        return self.gain

    def set_hp_frequency(self,frequency):
        if frequency >= self.lp_frequency:
            raise Exception('attempt to set SR560 highpass frequency to {:1.1g} Hz, which is >= current lowpass frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.lp_frequency.to(u.Hz).m))
        else:
            hp_freq_ind = [i for i, f in enumerate(frequency-self.frequencies[:12] >= 0.0*frequency.units) if not(f)][0] - 1 # restrict max HP frequency setting to 10kHz
            print(SR560_HighPassFrequency[self.hpf_keys[hp_freq_ind]].value)
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_HighPassFrequency[self.hpf_keys[hp_freq_ind]].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.hp_frequency = self.frequencies[hp_freq_ind]
        return self.hp_frequency

    def set_lp_frequency(self,frequency):
        if frequency <= self.hp_frequency:
            raise Exception('attempt to set SR560 lowpass frequency to {:1.1g} Hz, which is <= current highpass frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.hp_frequency.to(u.Hz).m))
        else:
            lp_freq_ind = [i for i, f in enumerate(frequency-self.frequencies <= 0.0 * frequency.units) if f][0]
            print(SR560_LowPassFrequency[self.lpf_keys[lp_freq_ind]].value)
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_LowPassFrequency[self.lpf_keys[lp_freq_ind]].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.lp_frequency = self.frequencies[lp_freq_ind]
        return self.lp_frequency

    def set_filter_type(self,filter_type):
        try:
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_Filter[filter_type].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.filter_type = SR560_Filter[filter_type]
        except:
            raise Exception('Unrecognized SR560 filter type: ' + str(filter_type))

    def set_gain_mode(self,gain_mode):
        try:
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_GainMode[gain_mode].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.gain_mode = SR560_GainMode[gain_mode]
        except:
            raise Exception('Unrecognized SR560 gain_mode: ' + str(gain_mode))

    def set_source(self,source):
        try:
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_Source[source].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.source = SR560_Source[source]
        except:
            raise Exception('Unrecognized SR560 source: ' + str(source))

    def set_coupling(self,coupling):
        try:
            self._rsrc.write('LALL')
            sleep(self.t_sleep)
            self._rsrc.write(SR560_Coupling[coupling].value)
            sleep(self.t_sleep)
            self._rsrc.write('UNLS')
            self.coupling = SR560_Coupling[coupling]
        except:
            raise Exception('Unrecognized SR560 coupling: ' + str(coupling))

    def blank_on(self):
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write(SR560_BlankToggle.on.value)
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')
        self.blank = True

    def blank_off(self):
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write(SR560_BlankToggle.off.value)
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')
        self.blank = False

    def invert_on(self):
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write(SR560_InvertToggle.on.value)
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')
        self.invert = True

    def invert_off(self):
        self._rsrc.write('LALL')
        sleep(self.t_sleep)
        self._rsrc.write(SR560_InvertToggle.off.value)
        sleep(self.t_sleep)
        self._rsrc.write('UNLS')
        self.invert = False
