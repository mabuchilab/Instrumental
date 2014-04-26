# -*- coding: utf-8 -*-
from instrumental import instrument, Q_
from instrumental.tools import DataSession
from numpy import sqrt

# Fix for Python 2
try: input = raw_input
except NameError: pass

# Set up scope and measurements
scope = instrument('SCOPE_C')
scope.set_measurement_params(1, 'amplitude', channel=2)
scope.set_measurement_params(2, 'amplitude', channel=4)
scope.set_measurement_params(3, 'max', channel=3)
scope.set_measurement_params(4, 'mean', channel=3)

scope.enable_measurement_stats()
scope.set_measurement_nsamps(256)

# Create data-taking session
ds = DataSession('Session')

for i in range(3):
    meas = {}
    meas['poling'] = Q_(int(input('Please enter the poling region number: ')))
    meas['temp'] = Q_(float(input('Please enter the crystal temp in C: ')), 'degC')

    stats_ch2 = scope.read_measurement_stats(1)
    stats_ch4 = scope.read_measurement_stats(2)

    meas['reference'] = stats_ch2['mean']
    meas['reference-error'] = stats_ch2['stddev']

    meas['reflected'] = stats_ch4['mean']
    meas['reflected-error'] = stats_ch4['stddev']

    # CH3 is annoying so we have to compute the amplitude
    ch3_max = scope.read_measurement_stats(3)
    ch3_baseline = scope.read_measurement_stats(4)
    meas['transmitted'] = ch3_max['mean'] - ch3_baseline['mean']
    meas['transmitted-error'] = sqrt(ch3_max['stddev']**2 + ch3_baseline['stddev']**2)

    print('-'*79)
    ds.add_measurement(meas)

ds.save_summary()
