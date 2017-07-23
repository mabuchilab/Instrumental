Integrating Your Driver with Instrumental
=========================================
To make your driver module integrate nicely with `Instrumental`, there are a few patterns that you should follow. 


Special Driver Variables
------------------------
These variables should be defined at top of your driver module, just below the imports.

`_INST_PARAMS`
    A list of strings indicating the parameter names which can be used to construct the instruments that this driver provides. The `Params` objects returned by `list_instruments()` should provide each of these parameters.
`_INST_CLASSES`
    Not required for VISA-based drivers. A list of strings indicating the names of all `Instrument` subclasses the driver module provides (typically only one).

    This enables you to avoid writing a driver-specific `_instrument()` function in most cases.
`_INST_VISA_INFO`
    Optional, and only applicable for VISA instruments. A dict mapping instrument class names to a tuple `(manufac, models)`, to be checked against the result of an `*IDN?` query. `manufac` is the manufacturer string, and `models` is a list of model strings.

    For instruments that support the `*IDN?` query, this allows us to directly find the correct driver and class to use.
`_INST_PRIORITY`
    Optional. An int (nominally 0-9) denoting the driver's priority. Lower-numbered drivers will be tried first. This is useful because some drivers are either slower, less reliable, or less commonly used than others, and should therefore be tried only after all other options are exhausted.


Functions
---------
These functions, if implemented, should be defined at the module level.

`list_instruments()`
    Optional for VISA-based drivers.

    This must return a list of `ParamSet`\s which correspond to each available device that this driver sees attached. Each `ParamSet` should contain all of the params listed in this driver's `_INST_PARAMS`.

`_instrument(paramset)`
    Optional. 

    Find and return the device corresponding to `paramset`. If this function is defined,
    `instrumental.instrument()` will use it to open instruments. Otherwise, the appropriate driver class is instantiated directly.

`_check_visa_support(visa_inst)`
    Optional, only applies to VISA-based drivers.

    Returns `True` if `visa_inst` is a device that is supported by this driver. This is only needed for VISA-based drivers where the device does not support the `*IDN?` query, and instead implements its own message-based protocol.


Writing Your `Instrument` Subclass
----------------------------------
Each driver subpackage defines its own subclass of `Instrument`, which your instrument class should subclass. For instance, all motion control instruments should inherit from `instrumental.drivers.motion.Motion`.


Writing `__init__()`
""""""""""""""""""""
Your class's `__init__()` method should have the following form:

General case
    `__init__(self, paramset[, settings...])`
VISA-based
    `__init__(self, paramset, visa_inst[, settings...])`

`paramset` is the `Params` used to create the instrument. For convenience, the special `settings` parameter is unpacked (using `**`) into the constructor. These settings should be given defaults if they are considered optional.

VISA-based instruments also take `visa_inst`, which is an already open `visa.Resource`. Typically you would save a reference to this as `self._inst`.


Special Methods
"""""""""""""""
There are also some special methods you may provide, all of which are optional.

`close(self)`
    Close the instrument. Useful for cleaning up per-instrument resources. This automatically gets called for each instrument upon program exit. The default implementation does nothing.

`_fill_out_paramset(self)`
    Flesh out the `Params` that the user provided. Usually you'd only reimplement this to provide a more efficient implementation than the default. The input params can be accessed and modified via `self._paramset`.

    The default implementation first checks which parameters were provided. If the user provided all parameters listed in the module's `_INST_PARAMS`, the params are considered complete. Otherwise, the driver's `list_instruments()` is called, and the the first matching set of params is used to fill in any missing entries in the input params.
