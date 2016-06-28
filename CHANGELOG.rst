Change Log
==========

Unreleased
----------

Added
"""""
- Package metadata now (mostly) consolidated in ``__about__.py``
- Support for DAQmx internal channels
- New NI driver, written using NiceLib, no longer requires PyDAQmx
- PCO:
  - Software ROI
  - Trigger mode support
  - Hotpixel correction
- Pixelfly:
  - Software ROI
  - Quantum efficiency functions
  - Multi-buffer capture sequences

Changed
"""""""
- Check for IDS library if Thorlabs uc480 dll isn't found
  (Issue #6, thanks Chris Timossi)
- ``u`` refers to Pint's ``_DEFAULT_REGISTRY``, making unpickling easier
- Fixed random assignment of DAQmx channels
  (Issue #15)
- Allow use of naked zeroes in ``check_units()``
- Use ``decorator`` module to preserve function signatures for wrapped functions
- Moved ``DEFAULT_KWDS`` into the Camera class
- Renamed ``check_enum()`` to ``as_enum()``
- PCO driver now uses the new NiceLib package

Removed
"""""""
- The ``NiceLib`` framework grew significantly and was split off into its own separate project


(0.2.1) - 2016-01-13
--------------------

Added
"""""
- Support for building cffi modules via setuptools
- Packaging support

Changed
"""""""
- instrumental.conf is now installed upon first-use. This allows us to eliminate the post_install
  script. Hopefully there will be future support (via wheels) to do this upon install instead
- slightly better error message for failure when importing a specified module in ``instrument()``

Removed
"""""""
- Outdated example scripts


(0.2) - 2015-12-15
------------------

Added
"""""
- Everything, technically, but recent changes include:
- ``NiceLib``, a class to aid wrapping typical DLLs
- Unit-checking decorators
- ``RemoteInstrument`` for using instruments controlled by a separate computer

Changed
"""""""
- Camera class is now an abstract base class with abstract methods and properties

Removed
"""""""
- ``FakeVISA`` (in favor of ``RemoteInstrument``)
