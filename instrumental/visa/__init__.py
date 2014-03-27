# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Package that supports use of a local VISA library as well as a remote
computer running VISA that acts as an Instrumental server.
"""

from __future__ import absolute_import

try:
    # Try to import 'true' pyvisa package
    from visa import *
except (ImportError, OSError):
    # If package or library not installed, use our fake client lib
    from .fakevisa import *
