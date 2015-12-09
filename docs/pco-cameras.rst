PCO Cameras
===========

.. toctree::

This module is for controlling PCO cameras that use the PCO.camera SDK. Note that not all PCO
cameras use this SDK, e.g. older Pixelfly cameras have their own SDK.


Installation
------------
This module requires the PCO SDK and the `cffi` package.

You should install the PCO SDK provided on PCO's website. Specifically, this module requires
`SC2_Cam.dll` to be available in your PATH, as well as any interface-specific DLLs. Firewire
requires `SC2_1394.dll`, and each type of Camera Link grabber requires its own DLL, e.g.
`sc2_cl_me4.dll` for a Silicon Software microEnable IV grabber card.


Module Reference
----------------

.. automodule:: instrumental.drivers.cameras.pco
    :members:
    :undoc-members:
