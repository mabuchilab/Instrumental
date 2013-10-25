# -*- coding: utf-8 -*-
# Copyright 2013 Nate Bogdanowicz

from pint import UnitRegistry

# Make a single UnitRegistry instance for the entire package
u = UnitRegistry()
Q_ = u.Quantity
