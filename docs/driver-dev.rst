:orphan:

Developing Drivers
==================
What we call a 'driver' in Instrumental is a high-level python interface to a hardware device.
These can be implemented in a number of ways. Frequently they are python bindings to lower-level C
hardware APIs, which can be simplified by using NiceLib. Another type of driver common to the lab
is an interface to an instrument that uses VISA (or SCPI). In this case, we can use PyVISA to
interface with the hardware, and focus on providing a high-level pythonic API.


Developing VISA Drivers
-----------------------
Since VISA uses a system-wide library to talk to a plethora of instruments, an Instrumental VISA
driver should use Instrumental's system-wide functions. See existing VISA-based drivers for how this
is done


Developing NiceLib Drivers
--------------------------
If you need to wrap a library or SDK with a C-style interface (most DLLs), you will probably want to
use NiceLib, which simplifies the process. You'll first write some code to generate mid-level
bindings for the library, then write your high-level bindings as a separate class, which will
inherit from the proper `Instrument` subclass. See the NiceLib documentation for details on how to
use it, and check out other NiceLib-based drivers to see how to integrate with Instrumental.


Driver Checklist
----------------
There are a few things that should be done to make a driver integrate really nicely with
Instrumental:

- Add documentation

  - Document methods using numpy-style docstrings

    - Use Instrumental docstring style guide

  - Add extra docs to show common usage patterns, if applicable

- Add supported device(s) to the list in ``overview.rst``
- Add support for `instrument()`
- Add support for `list_instruments()`
- Add support for saving
- Add a `close()` method if appropriate
- Add context manager support if appropriate
- Implement any required methods from the base class
- Ensure Python 3 compatibility
- Use Pint Units in your API
