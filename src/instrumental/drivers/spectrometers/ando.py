# -*- coding: utf-8 -*-
# Copyright 2023 Dodd Gray
"""
Driver module for Yokogawa/Ando spectrum analyzers.
Based on Nate's Tektronix scope driver
"""

from time import sleep

import numpy as np
import pyvisa
from pint import UndefinedUnitError
from pyvisa.constants import InterfaceType

from ... import Q_, u
from .. import VisaMixin
from . import Spectrometer

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'AQ6331': ('ANDO', ['AQ6331'])
}
# disp_visa_address = 'GPIB0::4::INSTR'
# osa_visa_address = 'GPIB0::23::INSTR'
# default_params = {'visa_address':osa_visa_address}

# def _check_visa_support(visa_inst):
#     id = visa_inst.query('ID?')
#     if id=='HP70951B\n':
#         return 'HPOSA'

class AQ6331(Spectrometer, VisaMixin):
    """
    A base class for Ando/Yokogawa AQ6331 series spectrum analyzers
    """
    # def __init__(self,params=None):
    #     """
    #     Create a spectrometer object that has the given VISA name *name* and connect
    #     to it. You can find available instrument names using the VISA
    #     Instrument Manager.
    #     """
    #     if params:
    #         self.inst = _instrument(params)
    #     else:
    #         self.inst = _instrument(default_params)
    #     self.inst.read_termination = "\n"  # Needed for stripping termination
    #     #self.inst.write("header OFF")
    #     self.inst.write_termination = ';'
    #     self.inst.write('TDF P') # set the trace data format to be decimal numbers in parameter units

    def _initialize(self):
        pass
        # self.read_termination = "\n"  # Needed for stripping termination
        # #self.inst.write("header OFF")
        # self.write_termination = ';'
        # self.write('TDF P') # set the trace data format to be decimal numbers in parameter units
        # if self.interface_type == InterfaceType.asrl:
        #     terminator = self.query('RS232:trans:term?').strip()
        #     self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        # elif self.interface_type == InterfaceType.usb:
        #     terminator = self.query('RS232:trans:term?').strip()
        #     self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        # elif self.interface_type == InterfaceType.tcpip:
        #     pass
        # else:
        #     pass
        #
        # self.write("header OFF")

    # def instrument_presets(self):
    #     self.write('IP')
    #     self.write('TDF P') # set the trace data format to be decimal numbers in parameter units

    def set_center_wavelength(self,cf):
        cf_nm = cf.to(u.nm).magnitude
        self.write('CTRWL{:4.2f}'.format(cf_nm))

    def get_center_wavelength(self):
        cf = np.float(self.query('CTRWL?')) * u.nm
        return cf

    def set_center_frequency(self,cf):
        cf_THz = cf.to(u.THz).magnitude
        self.write('CTRF{:4.2f}'.format(cf_THz))

    def get_center_frequency(self):
        cf = np.float(self.query('CTRF?')) * u.THz
        return cf

    def set_wavelength_span(self,sp):
        sp_nm = sp.to(u.nm).magnitude
        self.write('SPAN{:4.2f}'.format(sp_nm))

    def get_wavelength_span(self):
        sp = np.float(self.query('SPAN?')) * u.nm
        return sp

    def set_frequency_span(self,sp):
        sp_THz = sp.to(u.THz).magnitude
        self.write('SPANF{:4.2f}'.format(sp_THz))

    def get_frequency_span(self):
        sp = np.float(self.query('SPANF?')) * u.THz
        return sp

    def set_wavelength_resolution(self,rb):
        rb_nm = rb.to(u.nm).magnitude
        self.write('RESLN{:4.5f}'.format(rb_nm))

    def get_wavelength_resolution(self):
        rb = np.float(self.query('RESLN?')) * u.nm
        return rb
    def set_frequency_resolution(self,rb):
        rb_GHz = rb.to(u.GHz).magnitude
        self.write('RESLNF{:4.5f}'.format(rb_GHz))

    def get_frequency_resolution(self):
        rb = np.float(self.query('RESLNF?')) * u.GHz
        return rb

    def set_amplitude_units_PSD(self):
        self.write('LSUNT1')

    def set_amplitude_units_power(self):
        self.write('LSUNT0')

    def set_linear_yscale(self):
        self.write('LSCLLIN')

    def set_log_yscale(self,dB_per_division):
        self.write('LSCL{:2.1f}'.format(dB_per_division))

    def set_xscale_frequency(self):
        self.write('XUNT1')

    def set_xscale_wavelength(self):
        self.write('XUNT0')

    def get_xunit(self):
        if int(self.query('XUNT?')):
            return u.THz
        else:
            return u.nm

    def get_amplitude_units(self):
        psd = np.float(self.query('LSUNT?'))
        scale = np.float(self.query('LSCL?'))
        if psd:
            if scale:
                au = 1 / u.nm
            else:
                au = u.watt / u.nm
        else:
            if scale:
                au = u.dimensioness
            else:
                au = u.watt
        return au

    def turn_LPF_on(self):
        self.write('LPF1')

    def turn_LPF_off(self):
        self.write('LPF0')

    def set_avg_number(self,avg_number):
        self.write('AVG{:4.0f}'.format(avg_number))

    def get_avg_number(self):
        avg_number = np.float(self.query('AVG?'))
        return avg_number

    def set_number_points(self,n_pts):
        self.write('SMPL{:4.0f}'.format(n_pts))

    def get_number_points(self):
        n_pts = np.int(self.query('SMPL?'))
        return n_pts

    def get_spectrum(self,trace='A'):
        self.write('SD0') # sets string delimiter to ',' (1 would be CRLF)
        sleep(0.1)
        self.write('BD0') # sets block delimiter to CRLF (1 would be LF+EOI)
        sleep(0.1)
        self.write('HD0') # turns off 'header data'
        sleep(0.1)
        n_pts = self.get_number_points()
        yu = self.get_amplitude_units()
        amp = np.fromstring(self.query('LDAT'+trace),sep=',')[1:] * yu
        wl = np.fromstring(self.query('WDAT'+trace),sep=',')[1:] * u.nm
        return wl, amp



    def get_data(self, channel=1):
        """Retrieve a trace from the scope.

        Pulls data from channel `channel` and returns it as a tuple ``(t,y)``
        of unitful arrays.

        Parameters
        ----------
        channel : int, optional
            Channel number to pull trace from. Defaults to channel 1.

        Returns
        -------
        t, y : pint.Quantity arrays
            Unitful arrays of data from the scope. ``t`` is in seconds, while
            ``y`` is in volts.
        """
        inst = self.inst

        inst.write("data:source ch{}".format(channel))
        stop = int(inst.query("wfmpre:nr_pt?"))  # Get source's number of points
        stop = 10000
        inst.write("data:width 2")
        inst.write("data:encdg RIBinary")
        inst.write("data:start 1")
        inst.write("data:stop {}".format(stop))

        #inst.flow_control = 1  # Soft flagging (XON/XOFF flow control)
        tmo = inst.timeout
        inst.timeout = 10000
        inst.write("curve?")
        inst.read_termination = None
        inst.end_input = pyvisa.constants.SerialTermination.none
        # TODO: Change this to be more efficient for huge datasets
        with inst.ignore_warning(pyvisa.constants.VI_SUCCESS_MAX_CNT):
            s = inst.visalib.read(inst.session, 2)  # read first 2 bytes
            num_bytes = int(inst.visalib.read(inst.session, int(s[0][1]))[0])
            buf = ''
            while len(buf) < num_bytes:
                raw_bin, _ = inst.visalib.read(inst.session, num_bytes-len(buf))
                buf += raw_bin
                print(len(raw_bin))
        inst.end_input = pyvisa.constants.SerialTermination.termination_char
        inst.read_termination = '\n'
        inst.read()  # Eat termination
        inst.timeout = tmo
        raw_data_y = np.frombuffer(buf, dtype='>i2', count=int(num_bytes//2))

        # Get scale and offset factors
        x_scale = float(inst.query("wfmpre:xincr?"))
        y_scale = float(inst.query("wfmpre:ymult?"))
        x_zero = float(inst.query("wfmpre:xzero?"))
        y_zero = float(inst.query("wfmpre:yzero?"))
        x_offset = float(inst.query("wfmpre:pt_off?"))
        y_offset = float(inst.query("wfmpre:yoff?"))

        x_unit_str = inst.query("wfmpre:xunit?")[1:-1]
        y_unit_str = inst.query("wfmpre:yunit?")[1:-1]

        unit_map = {
            'U': '',
            'Volts': 'V'
        }

        x_unit_str = unit_map.get(x_unit_str, x_unit_str)
        try:
            x_unit = u.parse_units(x_unit_str)
        except UndefinedUnitError:
            x_unit = u.dimensionless

        y_unit_str = unit_map.get(y_unit_str, y_unit_str)
        try:
            y_unit = u.parse_units(y_unit_str)
        except UndefinedUnitError:
            y_unit = u.dimensionless

        raw_data_x = np.arange(1, stop+1)

        data_x = Q_((raw_data_x - x_offset)*x_scale + x_zero, x_unit)
        data_y = Q_((raw_data_y - y_offset)*y_scale + y_zero, y_unit)

        return data_x, data_y

    def set_measurement_params(self, num, mtype, channel):
        """Set the parameters for a measurement.

        Parameters
        ----------
        num : int
            Measurement number to set, from 1-4.
        mtype : str
            Type of the measurement, e.g. 'amplitude'
        channel : int
            Number of the channel to measure.
        """
        prefix = 'measurement:meas{}'.format(num)
        self.inst.write("{}:type {};source ch{}".format(prefix, mtype,
                                                        channel))

    def read_measurement_stats(self, num):
        """
        Read the value and statistics of a measurement.

        Parameters
        ----------
        num : int
            Number of the measurement to read from, from 1-4

        Returns
        -------
        stats : dict
            Dictionary of measurement statistics. Includes value, mean, stddev,
            minimum, maximum, and nsamps.
        """
        prefix = 'measurement:meas{}'.format(num)

        if not self.are_measurement_stats_on():
            raise Exception("Measurement statistics are turned off, "
                            "please turn them on.")

        # Potential issue: If we query for all of these values in one command,
        # are they guaranteed to be taken from the same statistical set?
        # Perhaps we should stop_acquire(), then run_acquire()...
        keys = ['value', 'mean', 'stddev', 'minimum', 'maximum']
        res = self.inst.query(prefix+':value?;mean?;stddev?;minimum?;maximum?;units?').split(';')
        units = res.pop(-1).strip('"')
        stats = {k: Q_(rval+units) for k, rval in zip(keys, res)}

        num_samples = int(self.inst.query('measurement:statistics:weighting?'))
        stats['nsamps'] = num_samples
        return stats

    def read_measurement_value(self, num):
        """Read the value of a measurement.

        Parameters
        ----------
        num : int
            Number of the measurement to read from, from 1-4

        Returns
        -------
        value : pint.Quantity
            Value of the measurement
        """
        prefix = 'measurement:meas{}'.format(num)

        raw_value, raw_units = self.inst.query('{}:value?;units?'.format(prefix)).split(';')
        units = raw_units.strip('"')
        return Q_(raw_value+units)

    def set_math_function(self, expr):
        """Set the expression used by the MATH channel.

        Parameters
        ----------
        expr : str
            a string representing the MATH expression, using channel variables
            CH1, CH2, etc. eg. 'CH1/CH2+CH3'
        """
        self.inst.write("math:type advanced")
        self.inst.write('math:define "{}"'.format(expr))

    def get_math_function(self):
        return self.inst.query("math:define?").strip('"')

    def run_acquire(self):
        """Sets the acquire state to 'run'"""
        self.inst.write("acquire:state run")

    def stop_acquire(self):
        """Sets the acquire state to 'stop'"""
        self.inst.write("acquire:state stop")

    def are_measurement_stats_on(self):
        """Returns whether measurement statistics are currently enabled"""
        res = self.inst.query("measu:statistics:mode?")
        return res not in ['OFF', '0']

    def enable_measurement_stats(self, enable=True):
        """Enables measurement statistics.

        When enabled, measurement statistics are kept track of, including
        'mean', 'stddev', 'minimum', 'maximum', and 'nsamps'.

        Parameters
        ----------
        enable : bool
            Whether measurement statistics should be enabled
        """
        # For some reason, the DPO 4034 uses ALL instead of ON
        self.inst.write("measu:statistics:mode {}".format('ALL' if enable else 'OFF'))

    def disable_measurement_stats(self):
        """Disables measurement statistics"""
        self.enable_measurement_stats(False)

    def set_measurement_nsamps(self, nsamps):
        """Sets the number of samples used to compute measurements.

        Parameters
        ----------
        nsamps : int
            Number of samples used to compute measurements
        """
        self.inst.write("measu:stati:weighting {}".format(nsamps))
