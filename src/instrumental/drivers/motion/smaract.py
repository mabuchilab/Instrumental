"""Driver module for Smaract stages.

Smaract proposes various controllers for their linear or rotation stages

Instrumental contains so far support for the SCU controller
The smaract libraries must be known by the system, adding their location on the system path
"""

from instrumental.drivers.motion import Motion


class SmaractDevice(Motion):
    pass
