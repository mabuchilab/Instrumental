# -*- coding: utf-8 -*-
# Copyright 2023 Dodd Gray
"""
Driver module for HP 70000 spectrum analyzer.
Based on Nate's Tektronix scope driver
"""

import numpy as np
from pint import UndefinedUnitError
from pyvisa.constants import VI_SUCCESS_MAX_CNT, SerialTermination

from ... import Q_, u
from .. import VisaMixin
from . import Spectrometer

_INST_PARAMS_ = ['visa_address']
_INST_VISA_INFO_ = {
    'AgilentOSA': ('AGILENT', ['86142B'])
}

class AgilentOSA(Spectrometer, VisaMixin):
    """
    A base class for HP 70000 series spectrum analyzers
    """
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('AGILENT', ['86142B'])

    def _initialize(self):
        self._rsrc.read_termination = '\n'  # Needed for stripping termination
        self._rsrc.timeout = 300
        self.write('FORMAT:DATA REAL32') # set the trace data format to be decimal numbers in parameter units

    def set_center_wavelength(self,cf):
        cf_nm = cf.to(u.nm).magnitude
        self.write('SENSE:WAVELENGTH:CENTER {:4.5f}NM'.format(cf_nm))

    def get_center_wavelength(self):
        cf = (float(self.query('SENSE:WAVELENGTH:CENTER?').strip('+')) * u.m).to(u.nm)
        return cf

    def set_wavelength_span(self,sp):
        sp_nm = sp.to(u.nm).magnitude
        self.write('SENSE:WAVELENGTH:SPAN {:4.5f}NM'.format(sp_nm))

    def get_wavelength_span(self):
        sp = (float(self.query('SENSE:WAVELENGTH:SPAN?').strip('+')) * u.m).to(u.nm)
        return sp

    def set_resolution_bandwidth(self,rb):
        rb_nm = rb.to(u.nm).magnitude
        self.write('SENSE:BANDwidth:RESolution {:4.5f}NM'.format(rb_nm))

    def get_resolution_bandwidth(self):
        rb = (float(self.query('SENSE:BANDwidth:RESolution?').strip('+')) * u.m).to(u.nm)
        return rb

    def set_amplitude_units(self,au):
        if au==u.watt:
            self.write('UNIT:POWER W')
        elif au==u.milliwatt:
            self.write('UNIT:POWER MW')
        elif au=='dBm':
            self.write('UNIT:POWER DBM')

    def get_amplitude_units(self):
        au_str = self.query('UNIT:POWER?')
        if au_str=='W':
            au = u.watt
        elif au_str=='MW':
            au = u.milliwatt
        elif au_str=='AUTO':
            au = u.dimensionless
        elif au_str=='DBM':
            au = u.dimensionless
        return au

    def set_sensitivity(self,sens):
        #sens = 10*np.log10(sens.to(u.milliwatt).magnitude)
        self.write('SENSe:POWer:AC:RANGe:LOW {:3.3E}'.format(sens.to(self.get_amplitude_units()).magnitude))

    def set_log_scale(self,scale):
        ### scale
        # self.write('LG {}DB'.format(scale))
        self.write("DISPlay:TRACe:Y:SCALe:SPACing LOGARITHMIC".format(scale))


    def set_linear_scale(self):
        self.write('LN')

    def set_reference_level(self,ref_level):
        ### scale
        if self.get_amplitude_units()==u.dimensionless:
            if ref_level.units==u.dimensionless:
                self.write('RL {:3.3E} DBM'.format(ref_level.magnitude))
            else:
                self.write('RL {:3.3E} DBM'.format(10*np.log10(ref_level.to(u.milliwatt).magnitude)))
        else:
            if ref_level.units==u.dimensionless:
                self.write('RL {:3.3E} mW'.format(10**(ref_level/10.0)))
            else:
                self.write('RL {:3.3E} mW'.format(ref_level.to(u.milliwatt).magnitude))

    def get_sensitivity(self):
        sens_dbm = float(self.query('SENSe:POWer:AC:RANGe:LOW?'))
        sens = (10**(sens_dbm/10.0) * u.milliwatt).to(u.watt)
        return sens

    def get_spectrum(self,trace='A'):
        self._rsrc.timeout = 10000
        au = self.get_amplitude_units()
        wl_center = self.get_center_wavelength()
        wl_span = self.get_wavelength_span()
        amp = np.fromstring(self.query(f'TRACE:DATA:Y? TR{trace}'),sep=',') * au
        wl_start = wl_center - wl_span / 2.0
        wl_stop = wl_center + wl_span / 2.0
        n_pts = len(amp)
        wl = Q_(np.linspace(wl_start.magnitude,wl_stop.magnitude,n_pts),wl_start.units)
        self._rsrc.timeout = 300
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
        inst.end_input = SerialTermination.none
        # TODO: Change this to be more efficient for huge datasets
        with inst.ignore_warning(VI_SUCCESS_MAX_CNT):
            s = inst.visalib.read(inst.session, 2)  # read first 2 bytes
            num_bytes = int(inst.visalib.read(inst.session, int(s[0][1]))[0])
            buf = ''
            while len(buf) < num_bytes:
                raw_bin, _ = inst.visalib.read(inst.session, num_bytes-len(buf))
                buf += raw_bin
                print(len(raw_bin))
        inst.end_input = SerialTermination.termination_char
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
