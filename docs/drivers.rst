Drivers
=======


Instrumental drivers allow you to control and read data from various hardware devices.

Some devices (e.g. Thorlabs cameras) have drivers that act as wrappers to their drivers' C
bindings, using `ctypes` or `cffi`. Others (e.g. Tektronix scopes and AFGs) utilize VISA and
`PyVISA`, its Python wrapper.  `PyVISA` requires a local installation of the VISA library (e.g.
NI-VISA) to interface with connected devices.


.. toctree::
    :maxdepth: 2
    :titlesonly:

    cameras
    daqs
    funcgenerators
    lasers
    lockins
    motion
    multimeters
    powermeters
    scopes
    spectrometers
    wavemeters


-------------------------------------------------------------------------------


Functions
---------

.. automodule:: instrumental.drivers
    :members:

Example
~~~~~~~
    >>> from instrumental import instrument
    >>> scope = instrument('my_scope_alias')
    >>> x, y = scope.get_data()


-------------------------------------------------------------------------------


.. _pip: http://www.pip-installer.org/
