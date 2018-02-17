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
from .. import VisaMixin, SCPI_Facet
from ..util import visa_context
from ... import u, Q_


MODEL_CHANNELS = {
    'TDS 210': 2,
    'TDS 220': 2,
    'TDS 224': 4,
    'TDS 1001B': 2,
    'TDS 1002B': 2,
    'TDS 1012B': 2,
    'TDS 2002B': 2,
    'TDS 2004B': 4,
    'TDS 2012B': 2,
    'TDS 2014B': 4,
    'TDS 2022B': 2,
    'TDS 2024B': 4,
    'TDS 3012': 2,
    'TDS 3012B': 2,
    'TDS 3012C': 2,
    'TDS 3014': 4,
    'TDS 3014B': 4,
    'TDS 3014C': 4,
    'TDS 3032': 2,
    'TDS 3032B': 2,
    'TDS 3032C': 2,
    'TDS 3034': 4,
    'TDS 3034B': 4,
    'TDS 3034C': 4,
    'TDS 3052': 2,
    'TDS 3052B': 2,
    'TDS 3052C': 2,
    'TDS 3054': 4,
    'TDS 3054B': 4,
    'TDS 3054C': 4,
    'MSO4032': 2,
    'DPO4032': 2,
    'MSO4034': 4,
    'DPO4034': 4,
    'MSO4054': 4,
    'DPO4054': 4,
    'MSO4104': 4,
    'DPO4104': 4,
}


class TekScope(Scope, VisaMixin):
    """
    A base class for Tektronix scopes. Supports at least TDS 3000 series as
    well as MSO/DPO 4000 series scopes.
    """
    def _initialize(self):
        if self.interface_type == InterfaceType.asrl:
            terminator = self.query('RS232:trans:term?').strip()
            self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        elif self.interface_type == InterfaceType.usb:
            terminator = self.query('RS232:trans:term?').strip()
            self._rsrc.read_termination = terminator.replace('CR', '\r').replace('LF', '\n')
        elif self.interface_type == InterfaceType.tcpip:
            pass
        else:
            pass

        self.write("header OFF")

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
        self.write("data:source ch{}".format(channel))
        stop = int(self.query("wfmpre:nr_pt?"))  # Get source's number of points
        stop = 10000
        self.write("data:width 2")
        self.write("data:encdg RIBinary")
        self.write("data:start 1")
        self.write("data:stop {}".format(stop))

        #self.resource.flow_control = 1  # Soft flagging (XON/XOFF flow control)

        with self.resource.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT),\
             visa_context(self.resource, timeout=10000, read_termination=None,
                          end_input=visa.constants.SerialTermination.none):

            self.write("curve?")
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

        self.resource.read()  # Eat termination

        num_points = int(num_bytes // 2)
        raw_data_y = np.frombuffer(buf, dtype='>i2', count=num_points)

        # Get scale and offset factors
        x_scale = float(self.query("wfmpre:xincr?"))
        y_scale = float(self.query("wfmpre:ymult?"))
        x_zero = float(self.query("wfmpre:xzero?"))
        y_zero = float(self.query("wfmpre:yzero?"))
        x_offset = float(self.query("wfmpre:pt_off?"))
        y_offset = float(self.query("wfmpre:yoff?"))

        x_unit_str = self.query("wfmpre:xunit?")[1:-1]
        y_unit_str = self.query("wfmpre:yunit?")[1:-1]

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
        self.write("{}:type {};source ch{}".format(prefix, mtype, channel))

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
        res = self.query(prefix+':value?;mean?;stddev?;minimum?;maximum?;units?').split(';')
        units = res.pop(-1).strip('"')
        stats = {k: Q_(rval+units) for k, rval in zip(keys, res)}

        num_samples = int(self.query('measurement:statistics:weighting?'))
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

        raw_value, raw_units = self.query('{}:value?;units?'.format(prefix)).split(';')
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
        self.write("math:type advanced")
        self.write('math:define "{}"'.format(expr))

    def get_math_function(self):
        return self.query("math:define?").strip('"')

    def run_acquire(self):
        """Sets the acquire state to 'run'"""
        self.write("acquire:state run")

    def stop_acquire(self):
        """Sets the acquire state to 'stop'"""
        self.write("acquire:state stop")

    @property
    def interface_type(self):
        return self.resource.interface_type

    @property
    def model(self):
        _, model, _, _ = self.query('*IDN?').split(',', 3)
        return model

    @property
    def channels(self):
        try:
            return MODEL_CHANNELS[self.model]
        except KeyError:
            raise KeyError('Unknown number of channels for this scope model')

    horizontal_scale = SCPI_Facet('hor:main:scale', convert=float, units='s')
    horizontal_delay = SCPI_Facet('hor:delay:pos', convert=float, units='s')
    math_function = property(get_math_function, set_math_function)


class StatScope(TekScope):
    def are_measurement_stats_on(self):
        """Returns whether measurement statistics are currently enabled"""
        res = self.query("measu:statistics:mode?")
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
        self.write("measu:statistics:mode {}".format('ALL' if enable else 'OFF'))

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
        self.write("measu:stati:weighting {}".format(nsamps))


class TDS_200(TekScope):
    """A Tektronix TDS 200 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 210', 'TDS 220', 'TDS 224'])


class TDS_1000(TekScope):
    """A Tektronix TDS 1000 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 1001B', 'TDS 1002B', 'TDS 1012B'])


class TDS_2000(TekScope):
    """A Tektronix TDS 2000 series oscilloscope"""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 2002B', 'TDS 2004B',
                                      'TDS 2012B', 'TDS 2014B',
                                      'TDS 2022B', 'TDS 2024B'])


class TDS_3000(StatScope):
    """A Tektronix TDS 3000 series oscilloscope."""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['TDS 3012', 'TDS 3012B', 'TDS 3012C',
                                      'TDS 3014', 'TDS 3014B', 'TDS 3014C',
                                      'TDS 3032', 'TDS 3032B', 'TDS 3032C',
                                      'TDS 3034', 'TDS 3034B', 'TDS 3034C',
                                      'TDS 3052', 'TDS 3052B', 'TDS 3052C',
                                      'TDS 3054', 'TDS 3054B', 'TDS 3054C',])


class MSO_DPO_4000(StatScope):
    """A Tektronix MSO/DPO 4000 series oscilloscope."""
    _INST_PARAMS_ = ['visa_address']
    _INST_VISA_INFO_ = ('TEKTRONIX', ['MSO4032', 'DPO4032', 'MSO4034', 'DPO4034',
                                      'MSO4054', 'DPO4054', 'MSO4104', 'DPO4104',])
