Writing Drivers
===============

.. toctree::
   :maxdepth: 2

   self
   visa-drivers
   nicelib-drivers
   integrating-drivers
   driver-params

-----------------------------------------------------------------------------------------------------

.. contents::
    :local:
    :depth: 2


Overview
--------
An `Instrumental` *driver* is a high-level Python interface to a hardware device. These can be implemented in a number of ways, but usually fall into one of two categories: message-based drivers and foreign function interface (ffi)-based drivers.

Many lab instruments--whether they use GPIB, RS-232, TCPIP, or USB--communicate using text-based messaging protocols. In this case, we can use `PyVISA`_ to interface with the hardware, and focus on providing a high-level pythonic API. See :doc:`visa-drivers` for more details.

Otherwise, the instrument is likely controlled via a library which is designed to be used by an application written in C. In this case, we can use `NiceLib`_ to greatly simplify the wrapping of the library. See :doc:`nicelib-drivers` for more details.

Generally a driver module should correspond to a single API/library which is being wrapped. For example, there are two separate drivers for Thorlabs cameras, `cameras.uc480` and `cameras.tsi`, each corresponding to a separate library.

.. _PyVISA: https://pyvisa.readthedocs.io/
.. _NiceLib: https://nicelib.readthedocs.io/


`Instrument` Goodies
--------------------
By subclassing `Instrument`, your class gets a number of features for free:

- Auto-closing on program exit (just provide a `close()` method)
- Saving of instruments via `save_instrument()`
- A context manager which automatically closes the instrument


Useful Utilities
----------------
Instrumental provides some commonly-used utilities for helping you to write drivers, including decorators and functions for helping to handle unitful arguments and enums. 

.. autofunction:: instrumental.drivers.util.check_units
.. autofunction:: instrumental.drivers.util.unit_mag
.. autofunction:: instrumental.drivers.util.check_enums
.. autofunction:: instrumental.drivers.util.as_enum
.. autofunction:: instrumental.drivers.util.visa_timeout_context


Driver Checklist
----------------
There are a few things that should be done to make a driver integrate really nicely with
Instrumental:

- Add documentation

  - Document methods using numpy-style docstrings
  - Add extra docs to show common usage patterns, if applicable
  - List dependencies following a template (both Python packages and external libraries)

- Add supported device(s) to the list in ``overview.rst``
- Add support for `instrument()`
- Add support for `list_instruments()`
- Add a `close()` method if appropriate
- Implement any required methods from the base class
- Ensure Python 3 compatibility
- Use Pint Units in your API
