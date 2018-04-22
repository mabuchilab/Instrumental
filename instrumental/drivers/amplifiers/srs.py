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


class SR570_HighFrequency(Enum):
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
    hf_30kHz = 'HFRQ 12'
    hf_100kHz = 'HFRQ 13'
    hf_300kHz = 'HFRQ 14'
    hf_1MHz = 'HFRQ 15'

class SR570_LowFrequency(Enum):
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
    Lo Freq = 0.03 Hz
    Hi Freq = 1 MHz
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
        self.bias_voltage = False
        self.input_offset_current_sign = SR570_InputOffsetCurrentSign.positive
        self.input_offset_current = 1 * u.pA
        self.input_offset_current = False
        self.low_frequency = 30 * u.mHz
        self.high_frequency = 1 * u.MHz
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
        self.hf_keys = [member for member in SR570_HighFrequency.__members__]
        self.lf_keys = [member for member in SR570_LowFrequency.__members__]
        self.sensitivity_keys = [member for member in SR570_Sensitivity.__members__]
        self.offset_current_level_keys = [member for member in SR570SR570_OffsetCurrentLevel.__members__]


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
        sensitivity_ind = [i for i, lvl in enumerate(sensitivity<=self.sensitivity_levels) if lvl][0]
        self._rsrc.write(SR570_Sensitivity[self.sensitivity_keys[sensitivity_ind].value)
        self.sensitivity = self.sensitivity_levels[sensitivty_ind]
        return self.sensitivty

    def set_offset_current(self,offset_current):
        oc_level_ind = [i for i, lvl in enumerate(abs(offset_current)<=self.offset_current_levels) if lvl][0]
        if offset_current < (0 * u.ampere):
            self._rsrc.write(SR570_InputOffsetCurrentSign.negative)
            self.offset_current = -1 * self.offset_current_levels[oc_level_ind]
        else:
            self._rsrc.write(SR570_InputOffsetCurrentSign.positive)
            self.offset_current = self.offset_current_levels[oc_level_ind]
        sleep(0.2) # allow time for SR570 to react to first request
        self._rsrc.write(self.offset_current_level_keys[oc_level_ind].value)
        return self.offset_current

    def set_filter_high_frequency(self,frequency):
        if frequency <= self.low_frequency:
            raise Exception('attempt to set SR570 high frequency to {:1.1g} Hz, which is <= current low frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.low_frequency.to(u.Hz).m))
        else:
            high_freq_ind = [i for i, f in enumerate(frequency<=self.frequencies) if f][0]
            self._rsrc.write(self.hf_keys[high_frequency_ind].value)
            self.high_frequency = self.frequencies[high_frequency_ind]
        return self.high_frequency

    def set_filter_low_frequency(self,frequency):
        if frequency >= self.high_frequency:
            raise Exception('attempt to set SR570 low frequency to {:1.1g} Hz, which is >= current high frequency setting, {:1.1g} Hz'.format(frequency.to(u.Hz).m,self.high_frequency.to(u.Hz).m))
        else:
            low_freq_ind = [i for i, f in enumerate(frequency>=self.frequencies) if not(f)][0] - 1
            self._rsrc.write(self.lf_keys[low_frequency_ind].value)
            self.low_frequency = self.frequencies[low_frequency_ind]
        return self.low_frequency

    def set_filter_type(self,fiter_type):
        try:
            self._rsrc.write(SR570_Filter[filter_type].value)
            self.filter_type = SR570_Filter[filter_type]
        except:
            raise Exception('Unrecognized SR570 filter type: ' + str(filter_type))

    def set_gain_mode(self,gain_mode):
        try:
            self._rsrc.write(SR570SR570_GainMode[gain_mode].value)
            self.gain_mode = SR570_Filter[gain_mode]
        except:
            raise Exception('Unrecognized SR570 gain_mode: ' + str(gain_mode))

    def offset_current_on(self):
        self._rsrc.write(SR570_InputOffsetCurrentToggle.on)
        self.input_offset_current = True

    def offset_current_off(self):
        self._rsrc.write(SR570_InputOffsetCurrentToggle.off)
        self.input_offset_current = False

    def blank_on(self):
        self._rsrc.write(SR570_BlankToggle.on)
        self.blank = True

    def blank_off(self):
        self._rsrc.write(SR570_BlankToggle.off)
        self.blank = False

    def invert_on(self):
        self._rsrc.write(SR570_InvertToggle.on)
        self.invert = True

    def invert_off(self):
        self._rsrc.write(SR570_InvertToggle.off)
        self.invert = False

    def bias_voltage_on(self):
        self._rsrc.write(SR570_BiasVoltageToggle.on)
        self.bias_voltage = True

    def bias_voltage_off(self):
        self._rsrc.write(SR570_Bias_voltageToggle.off)
        self.bias_voltage = False
