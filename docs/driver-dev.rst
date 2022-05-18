Writing Drivers
===============

.. contents::
    :local:
    :depth: 2


Examples
--------

.. toctree::
    :maxdepth: 2
    :titlesonly:

    visa-dev-example
    nicelib-dev-example

---------------------------------------------------------------------------------


Overview
--------
An Instrumental *driver* is a high-level Python interface to a hardware device. These can be implemented in a number of ways, but usually fall into one of two categories: message-based drivers and foreign function interface (FFI)-based drivers.

Many lab instruments---whether they use GPIB, RS-232, TCPIP, or USB---communicate using text-based messaging protocols. In this case, we can use `PyVISA`_ to interface with the hardware, and focus on providing a high-level pythonic API. See :ref:`visa-drivers` for more details.

Otherwise, the instrument is likely controlled via a library (DLL) which is designed to be used by an application written in C. In this case, we can use `NiceLib`_ to greatly simplify the wrapping of the library. See :ref:`nicelib-drivers` for more details.

Generally a driver module should correspond to a single API/library which is being wrapped. For example, there are two separate drivers for Thorlabs cameras, :mod:`instrumental.drivers.cameras.uc480` and :mod:`instrumental.drivers.cameras.tsi`, each corresponding to a separate library.

.. _PyVISA: https://pyvisa.readthedocs.io/
.. _NiceLib: https://nicelib.readthedocs.io/


By subclassing :class:`~instrumental.drivers.Instrument`, your class gets a number of features for free:

- Auto-closing on program exit (just provide a :meth:`~instrumental.drivers.Instrument.close` method)
- A context manager which automatically closes the instrument
- Saving of instruments via :meth:`~instrumental.drivers.Instrument.save_instrument`
- Integration with :class:`~instrumental.drivers.ParamSet`
- Integration with :class:`~instrumental.drivers.Facet`


.. _visa-drivers:

Writing VISA-based Drivers
--------------------------
To control instruments using message-based protocols, you should use `PyVISA`_, by making your driver class inherit from :class:`~instrumental.drivers.VisaMixin`. You can then use :func:`~instrumental.drivers.MessageFacet` or :func:`~instrumental.drivers.SCPI_Facet` to easily implement a lot of common functionality (see :doc:`facets` for more information). :class:`~instrumental.drivers.VisaMixin` provides a :attr:`~instrumental.drivers.VisaMixin.resource` property as well as :meth:`~instrumental.drivers.VisaMixin.write` and :meth:`~instrumental.drivers.VisaMixin.query` methods for your class.

If you're implementing ``_instrument()`` and need to open/access the VISA instrument/resource, you should use :func:`instrumental.drivers._get_visa_instrument` to take advantage of caching.

For a walkthough of writing a VISA-based driver, check out the :doc:`visa-dev-example`.

.. _nicelib-drivers:

Writing NiceLib-Based Drivers
-----------------------------
If you need to wrap a library or SDK with a C-style interface (most DLLs), you will probably want to use `NiceLib`_, which simplifies the process. You'll first write some code to generate mid-level bindings for the library, then write your high-level bindings as a separate class which inherits from the appropriate :class:`~instrumental.drivers.Instrument` subclass. See the `NiceLib`_ documentation for details on how to use it, and check out other NiceLib-based drivers to see how to integrate with Instrumental.

For a walkthough of writing a NiceLib-based driver, check out the :doc:`nicelib-dev-example`.



Integrating Your Driver with Instrumental
-----------------------------------------
To make your driver module integrate nicely with *Instrumental*, there are a few patterns that you should follow. 


.. _special-driver-variables:

Special Driver Variables
""""""""""""""""""""""""

.. note::

    Some old drivers use special variables that are defined on the module level, just below the imports. This method is now deprecated in favor of class-level variables. See :ref:`special-driver-variables-old` for info on the old variables.

When an instrument is created via :func:`~instrumental.drivers.list_instruments()`, Instrumental must find the proper driver to use. To avoid importing every driver module to check for the instrument, we use the statically generated file ``driver_info.py``. To register your driver in this file, *do not edit it directly*, but instead define special class attributes within your driver class:

:attr:`_INST_PARAMS_`
        A list of strings indicating the parameter names which can be used to construct the instruments that this driver class provides. The :class:`~instrumental.drivers.ParamSet` objects returned by :func:`~instrumental.drivers.list_instruments()` should provide each of these parameters. Usually VISA instruments just set ``_INST_PARAMS_ = ['visa_address']``.

:attr:`_INST_VISA_INFO_`
        (*Optional, only used for VISA instruments*) A tuple ``(manufac, models)``, to be checked against the result of an ``*IDN?`` query. ``manufac`` is the manufacturer string, and ``models`` is a list of model strings.

:attr:`_INST_PRIORITY_`
        (*Optional*) An int (nominally 0-9) denoting the driver's priority. Lower-numbered drivers will be tried first. This is useful because some drivers are either slower, less reliable, or less commonly used than others, and should therefore be tried only after all other options are exhausted.


To re-generate ``driver_info.py``, run ``python -m instrumental.parse_modules``. This will parse all of the driver code and look for classes defining the class attribute :attr:`_INST_PARAMS_`, adding them to its list of known drivers. The generated file contains all driver modules, driver classes, parameters, and required imports. For instanc::

    driver_info = OrderedDict([
        ('motion._kinesis.isc', {
            'params': ['serial'],
            'classes': ['K10CR1'],
            'imports': ['cffi', 'nicelib'],
        }),
        ('scopes.tektronix', {
            'params': ['visa_address'],
            'classes': ['MSO_DPO_2000', 'MSO_DPO_3000', 'MSO_DPO_4000', 'TDS_1000', 'TDS_200', 'TDS_2000', 'TDS_3000', 'TDS_7000'],
            'imports': ['pyvisa', 'visa'],
            'visa_info': {
                'MSO_DPO_2000': ('TEKTRONIX', ['MSO2012', 'MSO2014', 'MSO2024', 'DPO2012', 'DPO2014', 'DPO2024']),
            },
        }),
    ])



.. _special-driver-variables-old:

Special Driver Variables (deprecated method)
""""""""""""""""""""""""""""""""""""""""""""

Note that these old variable names lacked the trailing underscore.

:attr:`_INST_PARAMS`
        A list of strings indicating the parameter names which can be used to construct the instruments that this driver provides. The :class:`~instrumental.drivers.ParamSet` objects returned by :func:`~instrumental.drivers.list_instruments()` should provide each of these parameters.
:attr:`_INST_CLASSES`
        (*Not required for VISA-based drivers*) A list of strings indicating the names of all :class:`~instrumental.drivers.Instrument` subclasses the driver module provides (typically only one). This allows you to avoid writing a driver-specific ``_instrument()`` function in most cases.
:attr:`_INST_VISA_INFO`
        (*Optional, only used for VISA instruments*) A dict mapping instrument class names to a tuple ``(manufac, models)``, to be checked against the result of an ``*IDN?`` query. ``manufac`` is the manufacturer string, and ``models`` is a list of model strings.

        For instruments that support the ``*IDN?`` query, this allows us to directly find the correct driver and class to use.
:attr:`_INST_PRIORITY`
        (*Optional*) An int (nominally 0-9) denoting the driver's priority. Lower-numbered drivers will be tried first. This is useful because some drivers are either slower, less reliable, or less commonly used than others, and should therefore be tried only after all other options are exhausted.


.. _special-driver-functions:

Special Driver Functions
""""""""""""""""""""""""
These functions, if implemented, should be defined at the module level.

`list_instruments()`
    (*Optional for VISA-based drivers*) This must return a list of :class:`~instrumental.drivers.ParamSet`\s which correspond to each available device that this driver sees attached. Each :class:`~instrumental.drivers.ParamSet` should contain all of the params listed in this driver's :attr:`_INST_PARAMS`.

`_instrument(paramset)`
    (*Optional*) Must find and return the device corresponding to `paramset`. If this function is defined,
    :func:`instrumental.instrument` will use it to open instruments. Otherwise, the appropriate driver class is instantiated directly.

`_check_visa_support(visa_rsrc)`
    (*Optional, only applies to VISA-based drivers*) Must return the name of the ``Instrument`` subclass to use if ``visa_rsrc`` is a device that is supported by this driver, and ``None`` if it is not supported. ``visa_rsrc`` is a `pyvisa.resources.Resource` object. This function is only needed for VISA-based drivers where the device does not support the `*IDN?` query, and instead implements its own message-based protocol.


Writing Your `Instrument` Subclass
""""""""""""""""""""""""""""""""""
Each driver subpackage (e.g. ``instrumental.drivers.motion``) defines its own subclass of :class:`~instrumental.drivers.Instrument`, which you should use as the base class of your new instrument. For instance, all motion control instruments should inherit from :class:`instrumental.drivers.motion.Motion`.


Writing :meth:`~instrumental.drivers.Instrument._initialize`
~~~~~~~~~~~~~~~~~~~~~~~
:class:`~instrumental.drivers.Instrument` subclasses should implement an :meth:`~instrumental.drivers.Instrument._initialize` method to perform any required initialization (instead of `__init__`). For convenience, the special :ref:`settings parameter <settings-param>` is unpacked (using `**`) into this initializer. Any *optional* settings you support should be given default values in the function signature. No other arguments are passed to :meth:`~instrumental.drivers.Instrument._initialize`.

`_paramset` and other mixin-related attributes (e.g. ``resource`` for subclasses of :class`~instrumental.drivers.VisaMixin`) are already set before :meth:`~instrumental.drivers.Instrument._initialize` is called, so you may access them if you need to.


Special Methods
~~~~~~~~~~~~~~~
There are also some special methods you may provide, all of which are optional.

:meth:`~instrumental.drivers.Instrument.close`
    Close the instrument. Useful for cleaning up per-instrument resources. This automatically gets called for each instrument upon program exit. The default implementation does nothing.

:meth:`~instrumental.drivers.Instrument._fill_out_paramset`
    Flesh out the :class:`~instrumental.drivers.ParamSet` that the user provided. Usually you'd only reimplement this to provide a more efficient implementation than the default. The input params can be accessed and modified via `self._paramset`.

    The default implementation first checks which parameters were provided. If the user provided all parameters listed in the module's :attr:`~instrumental.drivers.Instrument._INST_PARAMS`, the params are considered complete. Otherwise, the driver's :func:`instrumental.drivers.list_instruments` is called, and the the first matching set of params is used to fill in any missing entries in the input params.


Driver Parameters
"""""""""""""""""
A :class:`~instrumental.drivers.ParamSet` is a set of identifying information, like serial number or name, that is used to find and identify an instrument. These :class:`~instrumental.drivers.ParamSet`\s are used heavily by :func:`~instrumental.drivers.instrument` and :func:`~instrumental.drivers.list_instruments`. There are some specially-handled parameters in addition to the ordinary ones, as described below.

You can customize how an :class:`~instrumental.drivers.Instrument`'s paramset is filled out by overriding the :meth:`~instrumental.drivers.Instrument._fill_out_paramset` method. The default implementation uses :func:`instrumental.drivers.list_instruments` to find a matching paramset, and updates the original paramset with any fields that are missing.


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
    A dict of extra settings which get passed as arguments to the instrument's constructor. These settings are separated from the other parameters because they are not considered *identifying information*, but simply configuration information. More specifically, changing the `settings` should never change which instrument the given :class:`~instrumental.drivers.ParamSet` will open.
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

In general, don't use vendor-specific names like `newport_id` (also avoid including underscores, for reasons that will become clear). Convenient vendor-specific parameters are automatically supported by :func:`~instrumental.drivers.instrument`. Say for example that the driver :mod:`instrumental.drivers.cameras.tsi` supports a :param:`serial` parameter. Then you can use any of the parameters `serial`, `tsi_serial`, `tsi_cam_serial`, and `cam_serial` to open the camera. The parameter name is split by underscores, then used to filter which modules are checked.

Note that `cam_serial` (vs `cameras_serial`) is not a typo. Each section is matched by substring, so you can even use something like `tsi_cam_ser`.


Useful Utilities
----------------
Instrumental provides some commonly-used utilities for helping you to write drivers, including decorators and functions for helping to handle unitful arguments and enums. 

.. autofunction:: instrumental.drivers.util.check_units
   :noindex:
.. autofunction:: instrumental.drivers.util.unit_mag
   :noindex:
.. autofunction:: instrumental.drivers.util.check_enums
   :noindex:
.. autofunction:: instrumental.drivers.util.as_enum
   :noindex:
.. autofunction:: instrumental.drivers.util.visa_timeout_context
   :noindex:


Driver-Writing Checklist
------------------------
There are a few things that should be done to make a driver integrate really nicely with Instrumental:

- Add any :ref:`special-driver-variables` your driver needs at the top of the driver module
- Implement any :ref:`special-driver-functions` you need
- Implement a :meth:`~instrumental.drivers.Instrument.close` method if appropriate
- Implement any required methods from the base class


Some other important things to keep in mind: 

- Use Pint Units in your API
- Ensure Python 3 compatibility
- Add documentation

  - Add supported device(s) to the list in :doc:`overview`
  - Document methods using numpy-style docstrings
  - Add extra docs to show common usage patterns, if applicable
  - List dependencies following a template (both Python packages and external libraries)
