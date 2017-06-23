# -*- coding: utf-8 -*-
# Copyright 2013-2017 Nate Bogdanowicz
"""
A simple plot of a sine wave with slider-adjustable parameters
"""
from instrumental import u, plotting as ip
from matplotlib import pyplot as plt
from numpy import sin, pi, arange

def curve(t, amp, freq, phase):
    return amp * sin(2*pi*u.rad*freq*t + phase)

# param_plot supports unitful parameters and variables
params = {
    'freq': 3*u.Hz,
    'amp': {
        'min':-10*u.V,
        'max':10*u.V,
        'init':5*u.V
    },
    'phase': {
        'min':0*u.rad,
        'max':2*pi*u.rad,
        'init':pi*u.rad
    }
}

t = arange(0.0, 1.0, 0.001) * u.s
ip.param_plot(t, curve, params)
plt.xlabel("Time [s]")
plt.ylabel("Amplitude [V]")
plt.title("Parameter Plot")
plt.show()
