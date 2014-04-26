# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz
"""
Driver module for Tektronix TDS3032 oscilloscopes.
"""

import numpy as np
from ... import visa
from instrumental import u, Q_
from . import Scope

class TDS_3032(Scope):
    """
    A Tektronix TDS3032 oscilloscope.
    """
    def __init__(self, name=None, instrument=None):
        """
        Create a scope object that has the given VISA name *name* and connect
        to it. You can find available instrument names using the VISA
        Instrument Manager.
        """
        if instrument:
            self.inst = instrument
        else:
            self.inst = visa.instrument(name)

    def get_data(self, channel=1):
        """
        Pull the data from channel *channel* and return it as a tuple
        ``(x,y)`` of unitful arrays.
        """
        inst = self.inst
        
        inst.write("data:source ch{}".format(channel))
        stop = int(inst.ask("wfmpre:nr_pt?")) # Get source's number of points
        stop = 10000
        inst.write("data:width 2")
        inst.write("data:encdg RIBinary")
        inst.write("data:start 1")
        inst.write("data:stop {}".format(stop))
        
        raw_bin = inst.ask("curve?")

        # Get scale and offset factors
        x_scale = float(inst.ask("wfmpre:xincr?"))
        y_scale = float(inst.ask("wfmpre:ymult?"))
        x_zero = float(inst.ask("wfmpre:xzero?"))
        y_zero = float(inst.ask("wfmpre:yzero?"))
        x_offset = float(inst.ask("wfmpre:pt_off?"))
        y_offset = float(inst.ask("wfmpre:yoff?"))
        
        x_unit = inst.ask("wfmpre:xunit?")[1:-1]
        y_unit = inst.ask("wfmpre:yunit?")[1:-1]
        
        raw_data_x = np.arange(1, stop+1)

        header_size = int(raw_bin[1]) + 2
        raw_data_y = np.frombuffer(raw_bin, dtype='>i2', offset=header_size)
        
        data_x = u[x_unit] * ((raw_data_x - x_offset)*x_scale + x_zero)
        data_y = u[y_unit] * ((raw_data_y - y_offset)*y_scale + y_zero)
        
        return data_x, data_y

    def set_measurement_params(self, num, mtype, channel):
        """
        Set the parameters for a measurement.

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
        self.inst.write("{}:type {};source ch{}".format(prefix, mtype, channel))

    def read_measurement_stats(self, num):
        """
        Read the value and statistics of a measurement.

        Returns
        -------
        stats : dict
            Dictionary of measurement statistics. Includes value, mean, stddev,
            minimum, maximum, and nsamps.
        """
        prefix = 'measurement:meas{}:'.format(num)

        if not self.are_measurement_stats_on():
            raise Exception("Measurement statistics are turned off, please turn them on.")

        # Potential issue: If we ask for all of these values in one command,
        # are they guaranteed to be taken from the same statistical set?
        # Perhaps we should stop_acquire(), then run_acquire()...
        keys = ['value', 'mean', 'stddev', 'minimum', 'maximum']
        res = self.inst.ask(prefix+'value?;mean?;stddev?;minimum?;maximum?;units?').split(';')
        units = res.pop(-1).strip('"')
        stats = {k:Q_(rval+units) for k,rval in zip(keys, res)}

        num_samples = int(self.inst.ask('measurement:statistics:weighting?'))
        stats['nsamps'] = num_samples
        return stats

    def read_measurement_value(self, num):
        """
        Read the value of a measurement.
        """
        prefix = 'measurement:meas{}:'.format(num)

        raw_value, raw_units = self.inst.ask('{}:value?;units?'.format(prefix)).split(';')
        units = raw_units.strip('"')
        return Q_(raw_value+units)
        
    def run_acquire(self):
        self.inst.write("acquire:state run")

    def stop_acquire(self):
        self.inst.write("acquire:state stop")

    def are_measurement_stats_on(self):
        res = self.inst.ask("measu:statistics:mode?")
        return res not in ['OFF', '0']

    def enable_measurement_stats(self, enable=True):
        # For some reason, the TDS4034 uses ALL instead of ON
        self.inst.write("measu:statistics:mode {}".format('ALL' if enable else 'OFF'))

    def disable_measurement_stats(self):
        self.enable_measurement_stats(False)

    def set_measurement_nsamps(self, nsamps):
        self.inst.write("measu:stati:weighting {}".format(nsamps))
