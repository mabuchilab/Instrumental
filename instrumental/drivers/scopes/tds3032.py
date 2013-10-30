# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz
"""
Driver module for Tektronix TDS3032 oscilloscopes.
"""

import numpy as np
import visa

class TDS_3032(object):
    """
    A Tektronix TDS3032 oscilloscope.
    """
    def __init__(self, name):
        """
        Create a scope object that has the given VISA name *name* and connect
        to it. You can find available instrument names using the VISA
        Instrument Manager.
        """
        self.inst = visa.instrument(name)

    def get_data(self, channel=1):
        """
        Pull the data from channel *channel* and return it as a tuple
        ``(x,y)`` of unitful arrays.
        """
        inst = self.inst
        
        inst.write("data:source ch{}".format(channel))
        inst.write("data:width 2")
        inst.write("data:encdg ascii")
        inst.write("data:start 1")
        inst.write("data:stop 10000")
        
        raw_asc = inst.ask("curve?")

        # Get scale and offset factors
        x_scale = float(inst.ask("wfmpre:xincr?"))
        y_scale = float(inst.ask("wfmpre:ymult?"))
        x_zero = float(inst.ask("wfmpre:xzero?"))
        y_zero = float(inst.ask("wfmpre:yzero?"))
        y_offset = float(inst.ask("wfmpre:yoff?"))
        
        x_unit = inst.ask("wfmpre:xunit?")[1:-1]
        y_unit = inst.ask("wfmpre:yunit?")[1:-1]
        
        raw_data_x = np.arange(1, 10001)
        raw_data_y = np.fromstring(raw_asc, sep=",")
        
        data_x = u[x_unit] * ((raw_data_x)*x_scale + x_zero)
        data_y = u[y_unit] * ((raw_data_y - y_offset)*y_scale + y_zero)
        
        return data_x, data_y


# List of pre-defined instruments
SCOPE_A = TDS_3032("TCPIP::171.64.84.116::INSTR")


if __name__=="__main__":
    from pylab import plot
    scope = SCOPE_A
    x,y = scope.get_data(1)
    plot(x, y)
    print("Done")
