Change Log
==========

(0.4) - 2017-11-13
------------------

Added
"""""
- User-configurable driver blacklist for ``list_instruments()``
- New parameter system using the new ``ParamSet`` class
- Convenience module for parsing and analyzing driver modules
- Default implementation of ``_instrument()`` for drivers
- ``LibError`` exception type for propagating errors from wrapped libs
- Default context manager in ``Instrument`` base class
- Auto-closing at exit of instruments inheriting from ``Instrument``
- ``visa_timeout_context`` context manager for setting VISA timeout
- Windows-based testing via AppVeyor
- Driver for the Princeton Instruments PICam interface
- Support for NI-DAQmx Base in the existing driver
- Context manager for ``daq.ni`` Tasks
- ``VisaMixin`` instrument mixin class
- ``Facet``s
- A deprecation decorator
- Automatic PyPI deployment via TravisCI and AppVeyor


Changed
"""""""
- Converted most drivers to use the new parameter system
- Reimplemented ``list_visa_instruments`` using a generator
- Improved developer-related docs
- Various improvements and bugfixes to ``daq.ni``
- Fixed bug in ``cameras.pixelfly`` doubleshutter mode


Removed
"""""""
- ``_ParamDict`` class


(0.3.1) - 2017-06-26
--------------------

Added
"""""
- ``.travis.yml``
- ``setup.cfg``

Changed
"""""""
- Fixed PyPI packaging whoopsie from 0.3


(0.3) - 2017-06-23
------------------

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
- Driver for Thorlabs FilterFlipper
- Driver for Thorlabs TDC001
- Driver for SRS SR850 lock-in amplifier
- Driver for Attocube ECC100
- Driver for Toptica FemtoFErb
- Driver for Thorlabs CCS specrometers
- Driver for Thorlabs TSI camera SDK
- Driver for HP 34401A Multimeter
- Driver for Thorlabs K10CR1 rotation stages
- Driver for modded SenTorr ion gauge
- Support for sharing instruments/objects across multiple clients of an
  Instrumental server

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
- Converted PCO driver to use NiceLib
- Converted NI driver to use NiceLib
- Converted Pixelfly driver to use NiceLib
- Converted UC480 driver to use NiceLib
- Improved error messages
- Added filtering of modules in ``list_instruments()``
- Added some fixes to improve Python 3 support
- Switched to using qtpy for handling Qt compatibility
- Added subsampling support to UC480 driver
- Added proper connection closing for PM100D power meters
- Documentation improvements

Removed
"""""""
- The ``NiceLib`` framework grew significantly and was split off into its own separate project
- The optics package was split off into a separate project named ``lentil``


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
