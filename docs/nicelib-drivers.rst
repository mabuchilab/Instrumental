Writing NiceLib-Based Drivers
-----------------------------
If you need to wrap a library or SDK with a C-style interface (most DLLs), you will probably want to use NiceLib, which simplifies the process. You'll first write some code to generate mid-level bindings for the library, then write your high-level bindings as a separate class which inherits from the appropriate `Instrument` subclass. See the `NiceLib documentation`_ for details on how to use it, and check out other NiceLib-based drivers to see how to integrate with Instrumental.

.. _NiceLib documentation: https://nicelib.readthedocs.io/
