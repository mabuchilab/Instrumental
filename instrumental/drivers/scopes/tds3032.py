# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz
"""
Driver module for Tektronix TDS3032 oscilloscopes.
"""

import numpy as np
from ... import visa
from instrumental import u
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
