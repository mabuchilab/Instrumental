# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz

from pint import UnitRegistry

# Make a single UnitRegistry instance for the entire package
u = UnitRegistry()
Q_ = u.Quantity

# Make common functions available directly
from .plotting import plot, param_plot
from .fitting import guided_trace_fit, guided_ringdown_fit
