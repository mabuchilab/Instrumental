Change Log
==========

(0.7) - 2022-5-29
-----------------

Added
"""""
- New drivers:
  - Keysight 81160A (thanks Sylvain Pelissier)
  - Tektronix MSO/DPO 3000 series oscilloscopes
  - Mad City Labs NanoDrive (thanks Sébastien Weber)
  - SmarAct SCU (thanks Sébastien Weber)
  - ThorLabs TLPM power meter (thanks Sébastien Weber)
- Exposure Facet for uc480 (thanks Sébastien Weber)
- Multi device NIDAQ Tasks (thanks Luka Skoric)

Changed
"""""""
- Define `_MSC_VER` in tlccs driver to fix choice of typedefs
- Fix Rigol function generator detection
- Overhauled Picam driver
  - Now uses `Camera` interface
  - Added Linux support
  - Added to the docs
 - Linked driver development references to the corresponding function/method/class (thanks Drew
   Risinger)

Removed
"""""""
- Use of deprecated `matplotlib.cbook.is_string_like`


(0.6) - 2020-8-29
-----------------

Added
"""""
- Groundwork for generic Thorlabs Kinesis support
- Support for simulated Kinesis instruments
- New drivers:
  - Agilent 33250A
  - Agilent E4400B signal generator
  - Agilent MXG signal generators
  - GW Instek GPD-3303S programmable linear DC power supply
  - ILX Lightwave 3724B laser diode controller
  - Newmark NSC-A1 single axis USB stepper motor controller
  - Rigol DS1000Z series oscilloscopes
  - Rigol DP700 series power supplies
  - Rohde & Schwarz FSEA 20 spectrum analyzer
  - Stanford Research Systems SR844 lock-in amplifier
  - Tektronix TDS7154 oscilloscopes
  - Thorlabs APT (for non-Windows-exclusive control of devices)
- Support for more models of Tektronix oscilloscope
- ``load_csv()`` function for Tektronix oscilloscopes
- Async functions for pulling data from Tektronix oscilloscopes
- Helper function for getting a valid power from the Newport 1830-C
- Better trigger support for NI DAQs
- Pixelclock support for cameras.uc480
- Support for loading saved instruments from an external driver
- Transaction context manager for ``VisaMixin``
- Facet-related:
  - ``ManualFacet``
  - ``FacetGroup``
  -  Simple observer/callback pattern


Changed
"""""""
- Fixed several uses of buffer/memoryview for Py2/3 compat
- Updated Picam driver to be compatible with newer NiceLib versions
- Fixed Py2/3 compat in remote module
- Converted more modules to use new log module
- Config directory changed to lowercase
- Stabilized the order of entries generated in ``driver_info.py``
- Improved uc480 error handling (#94)
- Fixed error for PCO cameras without ROI support (#104)
- Improved PCO camera support (thanks Zak Vendeiro)


Removed
"""""""



(0.5) - 2018-2-20
-----------------

Added
"""""
- Explicit support for Tektronix TDS 200, 3000, and MSO/DPO 4000 series scopes
- ``visa_context`` context manager
- More properties and Facets to scopes.tektronix
- More properties and Facets to cameras.uc480
- ``log`` module with ``log_to_screen()`` function
- tempcontrollers.covesion driver
- tempcontrollers.hcphotonics driver
- Special ``_close_resource`` method for visa instruments
- Import annotations for specifying driver reqs
- ``Instrument`` class-embedded ``_INSTR_`` attributes

Changed
"""""""
- Fixed some latent color/buffer issues in cameras.uc480's ``load_params()``
- Hid PCO camera scan dialog
- Sped up ``check_units()`` and ``unit_mag()``
- Added NiceLib header-cleanup hooks for recent changes to kinesis headers
- Converted NiceLib drivers to use NiceLib 0.5
- Added bounds handling to ``TekScope.get_data()``

Removed
"""""""


(0.4.2) - 2017-11-14
--------------------

Changed
"""""""
- Fixed bug ``list_instruments()`` bug introduced in 0.4.1
- Updated more documentation


(0.4.1) - 2017-11-14
--------------------

Added
"""""
- Filtering of VISA instruments by module in ``list_instruments()``

Changed
"""""""
- Fixed ``start_live_video`` AOI bug in ``cameras.uc480``
  (Issue #33, thanks Ivan Galinskiy)


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
