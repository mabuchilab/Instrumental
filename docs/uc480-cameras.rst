Thorlabs DCx (UC480) Cameras
============================

.. contents::
    :local:
    :depth: 2


Installation
------------

Summary
~~~~~~~
1. Install the `uc480 API`_ provided by Thorlabs.
2. Add the DLL to your PATH environment variable.
3. Run ``pip install pywin32 nicelib``.
4. Call ``list_instruments()``, which will auto-build the API bindings.

.. _uc480 API: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam


Details
~~~~~~~
1. Download and install ThorCam from the Thorlabs website, which comes with the uc480 API libraries. (Since these cameras are rebranded IDS cameras, you may instead install the IDS uEye software)
2. Make sure the path to the shared library (``uc480.dll``, ``uc480_64.dll``, ``ueye_api.dll``, or ``ueye_api_64.dll``) is added to your PATH. The library will usually be located in the Thorlabs or IDS folder inside your Program Files folder. On my system they are located within ``C:\Program Files\Thorlabs\Scientific Imaging\DCx Camera Support\Develop\Lib``.
3. Run ``pip install pywin32 nicelib`` on the command line to install the ``pywin32`` and ``nicelib`` packages.
4. Use ``list_instruments()`` to see if your camera shows up. This will automatically build the bindings to the DLL. If this doesn't work (and your camera is plugged in an works with the ThorCam software), try to import the driver module directly: ``from instrumental.drivers.cameras import uc480``. If this fails, the error should give you information about what went wrong. Be sure to check out the :doc:`faq` page for more information, and  you can use the `mailing list`_ or `GitHub`_ if you need additional help.

.. _GitHub: https://github.com/mabuchilab/Instrumental/issues
.. _mailing list: https://groups.google.com/d/forum/instrumental-lib


****


Module Reference
----------------

.. automodule:: instrumental.drivers.cameras.uc480
    :members:
    :inherited-members:
    :undoc-members:


****


Changelog
---------

Unreleased
~~~~~~~~~~
- Added ``gain_boost``, ``master_gain``, ``gamma``, ``blacklevel``, and many ``auto-x`` Facets/properties
- Made sure framerate is set before exposure time

Version 0.4.1
~~~~~~~~~~~~~
- Fixed AOI-related error on calling ``start_live_video()``

Version 0.4
~~~~~~~~~~~
- Converted to use new-style Instrument initialization
- Added error code to UC480 errors
- Converted to use new-style Params

Version 0.3
~~~~~~~~~~~
- Removed deprecated usage of 'is_SetImageSize'
- Ported driver to use ``NiceLib`` instead of ``ctypes``
- Added subsampling support
- Added gain setting
- Added triggering support
- Added support for using IDS library

Version 0.2
~~~~~~~~~~~
- Initial driver release
