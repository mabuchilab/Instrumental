# -*- coding: utf-8 -*-
# Copyright 2013-2017 Nate Bogdanowicz
"""
Driver module for Tektronix oscilloscopes. Currently supports

* TDS 3000 series
* MSO/DPO 4000 series
"""
import visa
from pyvisa.constants import InterfaceType
import numpy as np
from pint import UndefinedUnitError
from . import Scope
from ... import u, Q_

_INST_PARAMS = ['visa_address']
_INST_VISA_INFO = {
    'TDS_200': ('TEKTRONIX', ['TDS 210']),
    'TDS_3000': ('TEKTRONIX', ['TDS 3032', 'TDS 3034B']),
    'MSO_DPO_4000': ('TEKTRONIX', ['MSO4034', 'DPO4034'])
}


class TekScope(Scope):
    """
    A base class for Tektronix scopes. Supports at least TDS 3000 series as
    well as MSO/DPO 4000 series scopes.
    """
    def _initialize(self):
        if self._rsrc.interface_type == InterfaceType.asrl:
            terminator = self._rsrc.query('RS232:trans:term?').strip()
            self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        elif self._rsrc.interface_type == InterfaceType.usb:
            pass
        elif self._rsrc.interface_type == InterfaceType.tcpip:
            pass
        else:
            pass

        self._rsrc.write("header OFF")

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
        inst = self._rsrc

        inst.write("data:source ch{}".format(channel))
        stop = int(inst.query("wfmpre:nr_pt?"))  # Get source's number of points
        stop = 10000
        inst.write("data:width 2")
        inst.write("data:encdg RIBinary")
        inst.write("data:start 1")
        inst.write("data:stop {}".format(stop))

        #inst.flow_control = 1  # Soft flagging (XON/XOFF flow control)
        old_read_termination = inst.read_termination
        old_end_input = inst.end_input
        old_timeout = inst.timeout

        inst.timeout = 10000
        inst.read_termination = None
        inst.end_input = visa.constants.SerialTermination.none
        inst.write("curve?")

        with inst.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT):
            (_, width), _ = inst.visalib.read(inst.session, 2)  # read first 2 bytes
            num_bytes = int(inst.visalib.read(inst.session, int(width))[0])
            buf = bytearray(num_bytes)
            cursor = 0
            while cursor < num_bytes:
                raw_bin, _ = inst.visalib.read(inst.session, num_bytes-cursor)
                buf[cursor:cursor+len(raw_bin)] = raw_bin
                cursor += len(raw_bin)
                print(cursor)

        inst.end_input = old_end_input
        inst.read_termination = old_read_termination
        inst.timeout = old_timeout
        inst.read()  # Eat termination

        num_points = int(num_bytes // 2)
        raw_data_y = np.frombuffer(buf, dtype='>i2', count=num_points)

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

        raw_data_x = np.arange(1, num_points+1)

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
        self._rsrc.write("{}:type {};source ch{}".format(prefix, mtype,
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
        res = self._rsrc.query(prefix+':value?;mean?;stddev?;minimum?;maximum?;units?').split(';')
        units = res.pop(-1).strip('"')
        stats = {k: Q_(rval+units) for k, rval in zip(keys, res)}

        num_samples = int(self._rsrc.query('measurement:statistics:weighting?'))
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

        raw_value, raw_units = self._rsrc.query('{}:value?;units?'.format(prefix)).split(';')
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
        self._rsrc.write("math:type advanced")
        self._rsrc.write('math:define "{}"'.format(expr))

    def get_math_function(self):
        return self._rsrc.query("math:define?").strip('"')

    def run_acquire(self):
        """Sets the acquire state to 'run'"""
        self._rsrc.write("acquire:state run")

    def stop_acquire(self):
        """Sets the acquire state to 'stop'"""
        self._rsrc.write("acquire:state stop")

    def are_measurement_stats_on(self):
        """Returns whether measurement statistics are currently enabled"""
        res = self._rsrc.query("measu:statistics:mode?")
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
        self._rsrc.write("measu:statistics:mode {}".format('ALL' if enable else 'OFF'))

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
        self._rsrc.write("measu:stati:weighting {}".format(nsamps))


class TDS_200(TekScope):
    """A Tektronix TDS 200 series oscilloscope"""
    pass


class TDS_3000(TekScope):
    """A Tektronix TDS 3000 series oscilloscope."""
    pass


class MSO_DPO_4000(TekScope):
    """A Tektronix MSO/DPO 4000 series oscilloscope."""
    pass
