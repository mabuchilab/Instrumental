Writing Drivers
===============

.. contents::
    :local:
    :depth: 2

---------------------------------------------------------------------------------


Overview
--------
An Instrumental *driver* is a high-level Python interface to a hardware device. These can be implemented in a number of ways, but usually fall into one of two categories: message-based drivers and foreign function interface (FFI)-based drivers.

Many lab instruments---whether they use GPIB, RS-232, TCPIP, or USB---communicate using text-based messaging protocols. In this case, we can use `PyVISA`_ to interface with the hardware, and focus on providing a high-level pythonic API. See :ref:`visa-drivers` for more details.

Otherwise, the instrument is likely controlled via a library (DLL) which is designed to be used by an application written in C. In this case, we can use `NiceLib`_ to greatly simplify the wrapping of the library. See :ref:`nicelib-drivers` for more details.

Generally a driver module should correspond to a single API/library which is being wrapped. For example, there are two separate drivers for Thorlabs cameras, `cameras.uc480` and `cameras.tsi`, each corresponding to a separate library.

.. _PyVISA: https://pyvisa.readthedocs.io/
.. _NiceLib: https://nicelib.readthedocs.io/


By subclassing `Instrument`, your class gets a number of features for free:

- Auto-closing on program exit (just provide a `close()` method)
- A context manager which automatically closes the instrument
- Saving of instruments via `save_instrument()`
- Integration with `ParamSet`
- Integration with `Facet`


.. _visa-drivers:

Writing VISA-based Drivers
--------------------------
To control instruments using message-based protocols, you should use `PyVISA`_, by making your driver class inherit from `VisaMixin`. You can then use `MessageFacet` or `SCPI_Facet` to easily implement a lot of common functionality (see :doc:`facets` for more information). `VisaMixin` provides a ``resource`` property as well as ``write`` and ``query`` methods for your class.

If you're implementing ``_instrument()`` and need to open/access the VISA instrument/resource, you should use ``_get_visa_instrument()`` to take advantage of caching.

.. _nicelib-drivers:

Writing NiceLib-Based Drivers
-----------------------------
If you need to wrap a library or SDK with a C-style interface (most DLLs), you will probably want to use NiceLib, which simplifies the process. You'll first write some code to generate mid-level bindings for the library, then write your high-level bindings as a separate class which inherits from the appropriate `Instrument` subclass. See the `NiceLib`_ documentation for details on how to use it, and check out other NiceLib-based drivers to see how to integrate with Instrumental.



Integrating Your Driver with Instrumental
-----------------------------------------
To make your driver module integrate nicely with `Instrumental`, there are a few patterns that you should follow. 


.. _special-driver-variables:

Special Driver Variables
""""""""""""""""""""""""
These variables should be defined at top of your driver module, just below the imports.

`_INST_PARAMS`
    A list of strings indicating the parameter names which can be used to construct the instruments that this driver provides. The `ParamSet` objects returned by `list_instruments()` should provide each of these parameters.
`_INST_CLASSES`
    (*Not required for VISA-based drivers*) A list of strings indicating the names of all `Instrument` subclasses the driver module provides (typically only one). This allows you to avoid writing a driver-specific `_instrument()` function in most cases.
`_INST_VISA_INFO`
    (*Optional, only used for VISA instruments*) A dict mapping instrument class names to a tuple `(manufac, models)`, to be checked against the result of an `*IDN?` query. `manufac` is the manufacturer string, and `models` is a list of model strings.

    For instruments that support the `*IDN?` query, this allows us to directly find the correct driver and class to use.
`_INST_PRIORITY`
    (*Optional*) An int (nominally 0-9) denoting the driver's priority. Lower-numbered drivers will be tried first. This is useful because some drivers are either slower, less reliable, or less commonly used than others, and should therefore be tried only after all other options are exhausted.


.. _special-driver-functions:

Special Driver Functions
""""""""""""""""""""""""
These functions, if implemented, should be defined at the module level.

`list_instruments()`
    (*Optional for VISA-based drivers*) This must return a list of `ParamSet`\s which correspond to each available device that this driver sees attached. Each `ParamSet` should contain all of the params listed in this driver's `_INST_PARAMS`.

`_instrument(paramset)`
    (*Optional*) Must find and return the device corresponding to `paramset`. If this function is defined,
    `instrumental.instrument()` will use it to open instruments. Otherwise, the appropriate driver class is instantiated directly.

`_check_visa_support(visa_inst)`
    (*Optional, only applies to VISA-based drivers*) Must return ``True`` if `visa_inst` is a device that is supported by this driver. This is only needed for VISA-based drivers where the device does not support the `*IDN?` query, and instead implements its own message-based protocol.


Writing Your `Instrument` Subclass
""""""""""""""""""""""""""""""""""
Each driver subpackage (e.g. ``instrumental.drivers.motion``) defines its own subclass of `Instrument`, which you should use as the base class of your new instrument. For instance, all motion control instruments should inherit from `instrumental.drivers.motion.Motion`.


Writing `_initialize()`
~~~~~~~~~~~~~~~~~~~~~~~
`Instrument` subclasses should implement an `_initialize()` method to perform any required initialization (instead of `__init__`). For convenience, the special :ref:`settings parameter <settings-param>` is unpacked (using `**`) into this initializer. Any *optional* settings you support should be given default values in the function signature. No other arguments are passed to `_initialize()`.

`_paramset` and other mixin-related attributes (e.g. ``resource`` for subclasses of `VisaMixin`) are already set before `_initialize()` is called, so you may access them if you need to.


Special Methods
~~~~~~~~~~~~~~~
There are also some special methods you may provide, all of which are optional.

`close(self)`
    Close the instrument. Useful for cleaning up per-instrument resources. This automatically gets called for each instrument upon program exit. The default implementation does nothing.

`_fill_out_paramset(self)`
    Flesh out the `ParamSet` that the user provided. Usually you'd only reimplement this to provide a more efficient implementation than the default. The input params can be accessed and modified via `self._paramset`.

    The default implementation first checks which parameters were provided. If the user provided all parameters listed in the module's `_INST_PARAMS`, the params are considered complete. Otherwise, the driver's `list_instruments()` is called, and the the first matching set of params is used to fill in any missing entries in the input params.


Driver Parameters
"""""""""""""""""
A `ParamSet` is a set of identifying information, like serial number or name, thar is used to find and identify an instrument. These `ParamSet`\s are used heavily by ``instrument()`` and ``list_instruments()``. There are some specially-handled parameters in addition to the ordinary ones, as described below.

You can customize how an instrument's paramset is filled out by overriding the ``_fill_out_paramset`` method. The default implementation uses ``list_instruments`` to find a matching paramset, and updates the original paramset with any fields that are missing.


Special params
~~~~~~~~~~~~~~
There are a few parameters that are treated specially. These include:

module
    The name of the driver module, relative to the `drivers` package, e.g. `scopes.tektronix`.
classname
    The name of the class to which these parameters apply.
server
    The address of an instrument server which should be used to open the remote instrument.

.. _settings-param:

settings
    A dict of extra settings which get passed as arguments to the instrument's constructor. These settings are separated from the other parameters because they are not considered *identifying information*, but simply configuration information. More specifically, changing the `settings` should never change which instrument the given `ParamSet` will open.
visa_address
    The address string of a VISA instrument. If this is given, Instrumental will assume the parameters refer to a VISA instrument, and will try to open it with one of the VISA-based drivers.

Common params
~~~~~~~~~~~~~
Driver-defined parameters can be named pretty much anything (other than the special names given above). However, they should typically fall into a small set of commonly shared names to make the user's life easier. Some commonly-used names you should consider using include:

- serial
- model
- number
- id
- name
- port

In general, don't use vendor-specific names like `newport_id` (also avoid including underscores, for reasons that will become clear). Convenient vendor-specific parameters are automatically supported by `instrument()`. Say for example that the driver `cameras.tsi` supports a `serial` parameter. Then you can use any of the parameters `serial`, `tsi_serial`, `tsi_cam_serial`, and `cam_serial` to open the camera. The parameter name is split by underscores, then used to filter which modules are checked.

Note that `cam_serial` (vs `cameras_serial`) is not a typo. Each section is matched by substring, so you can even use something like `tsi_cam_ser`.


Useful Utilities
----------------
Instrumental provides some commonly-used utilities for helping you to write drivers, including decorators and functions for helping to handle unitful arguments and enums. 

.. autofunction:: instrumental.drivers.util.check_units
.. autofunction:: instrumental.drivers.util.unit_mag
.. autofunction:: instrumental.drivers.util.check_enums
.. autofunction:: instrumental.drivers.util.as_enum
.. autofunction:: instrumental.drivers.util.visa_timeout_context


Driver-Writing Checklist
------------------------
There are a few things that should be done to make a driver integrate really nicely with Instrumental:

- Add any :ref:`special-driver-variables` your driver needs at the top of the driver module
- Implement any :ref:`special-driver-functions` you need
- Implement a `close()` method if appropriate
- Implement any required methods from the base class


Some other important things to keep in mind: 

- Use Pint Units in your API
- Ensure Python 3 compatibility
- Add documentation

  - Add supported device(s) to the list in ``overview.rst``
  - Document methods using numpy-style docstrings
  - Add extra docs to show common usage patterns, if applicable
  - List dependencies following a template (both Python packages and external libraries)
