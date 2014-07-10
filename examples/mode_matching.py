# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from numpy import cos, sin, arcsin
import matplotlib.pyplot as plt
from instrumental.optics.optical_elements import Space, Mirror, Interface
from instrumental.optics.beam_tools import find_cavity_modes
from instrumental.optics.beam_plotting import plot_profile
from instrumental import Q_

# Cavity Parameters (lengths in meters)
R = Q_('10 cm')
d = Q_('250 um')
d1 = d2 = d3 = d
n0 = 1
n = 1.51
lambda0 = Q_('852 nm')

# Curved and flat mirror thicknesses
tc = Q_('.165 in')
tf = Q_('.250 in')

# Path length through interior of mirror optics (given 30deg incidence angle)
D_c = tc/cos(arcsin(n0/n * sin(Q_('30 deg'))))
D_f = tf/cos(arcsin(n0/n * sin(Q_('30 deg'))))

cavity_elems = [Mirror(R, aoi='30 deg'), Space(d1), Mirror(), Space(d2),
                Mirror(), Space(d3)]

outcoupling_c_elems = [Interface(n0, n, R, aoi='30 deg'), Space(D_c, n),
                       Interface(n, n0, aot='30 deg'), Space('17 mm')]

outcoupling_f_elems = [Interface(n0, n, aoi='30 deg'), Space(D_f, n),
                       Interface(n, n0, aot='30 deg'), Space('25 mm')]

names = ['Curved Mirror', 'Flat Mirror 1', 'Flat Mirror 2']
names_c = ['', '', '', '', 'Backside of Curved Mirror']
names_f = ['', '', '', 'Backside of Flat Mirror']

qt_r, qs_r = find_cavity_modes(cavity_elems)

# Beam profile inside the cavity
plot_profile(qt_r, qs_r, lambda0, cavity_elems, cyclical=True, names=names)

# Beam profile inside the cavity and outcoupling through the curved mirror
plot_profile(qt_r, qs_r, lambda0, cavity_elems+outcoupling_c_elems,
             show_axis=True, names=names_c)

# Same, except the line is no longer the spot-size w, but rather the radius at
# which knife-edge clipping is one part per million (1e-6)
plot_profile(qt_r, qs_r, lambda0, cavity_elems+outcoupling_c_elems,
             show_axis=True, clipping=1e-6)

# Beam profile inside the cavity and outcoupling through a flat mirror
plot_profile(qt_r, qs_r, lambda0, cavity_elems[:4]+outcoupling_f_elems,
             show_axis=True, names=names_f, zeroat=6)

plt.legend()
plt.show()
