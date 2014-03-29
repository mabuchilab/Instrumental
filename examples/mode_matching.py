# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from numpy import cos, sin, arccos, arcsin, deg2rad
import matplotlib.pyplot as plt
from instrumental.optics.optical_elements import Space, Mirror, Interface
from instrumental.optics.beam_tools import find_cavity_modes
from instrumental.optics.beam_plotting import plot_profile, plot_profile_and_RoC

# Cavity Parameters (lengths in meters)
R = 0.1
d = 250e-6
d1 = d
d2 = d
d3 = d
n0 = 1
n = 1.51
lambda0 = 852e-9

# Curved and flat mirror thicknesses
tc = .165 * 25.4e-3
tf = .250 * 25.4e-3

# Path length through interior of mirror optics (given 30deg incidence angle)
D_c = tc/cos(arcsin(n0/n * sin(deg2rad(30))))
D_f = tf/cos(arcsin(n0/n * sin(deg2rad(30))))

cavity_elems = [Mirror(R, aoi=30), Space(d1), Mirror(), Space(d2),
                Mirror(), Space(d3)]

outcoupling_c_elems = [Interface(n0, n, R, aoi=30), Space(D_c, n),
                       Interface(n, n0, aot=30), Space(17e-3)]

outcoupling_f_elems = [Interface(n0, n, aoi=30), Space(D_f, n),
                       Interface(n, n0, aot=30), Space(25e-3)]

names = ['Curved Mirror', 'Flat Mirror 1', 'Flat Mirror 2']
names_c = ['', '', '', '', 'Backside of Curved Mirror']
names_f = ['','','','Backside of Flat Mirror']

qt_r, qs_r = find_cavity_modes(cavity_elems)

# Beam profile inside the cavity
plot_profile(qt_r, qs_r, lambda0, cavity_elems, cyclical=True, names=names)

# Beam profile inside the cavity and outcoupling through the curved mirror
plot_profile(qt_r, qs_r, lambda0, cavity_elems+outcoupling_c_elems, show_axis=True, names=names_c)

# Same, except the line is no longer the spot-size w, but rather the radius at
# which knife-edge clipping is one part per million (1e-6)
plot_profile(qt_r, qs_r, lambda0, cavity_elems+outcoupling_c_elems, show_axis=True, clipping=1e-6)

# Beam profile inside the cavity and outcoupling through a flat mirror
plot_profile(qt_r, qs_r, lambda0, cavity_elems[:4]+outcoupling_f_elems, show_axis=True, names=names_f, zeroat=6)

plt.legend()
plt.show()
