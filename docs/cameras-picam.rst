Picam Cameras
=============

.. toctree::


Installation
------------
This module requires the Picam SDK and the `NiceLib` package. Tested to work on Windows and Linux.

On Linux, you must set the ``GENICAM_ROOT_V2_4`` environment variable to the path to genicam (probably ``/opt/pleora/ebus_sdk/x86_64/lib/genicam``) and ensure that Picam's lockfile directory exists (the Picam SDK installer isn't good about doing this).

On Windows, the DLLs ``Picam.dll``, ``Picc.dll``, ``Pida.dll``, and ``Pidi.dll`` must be copied to a
directory on the system path. Note that the DLLs found first on the system path must match the
version of the headers installed with the Picam SDK.


Module Reference
----------------

.. py:currentmodule:: instrumental.drivers.cameras.picam


In addition to the documented methods, instances of :py:class:`PicamCamera` have a ``params`` attribute which contains the camera's Picam parameters. Each parameter implements ``get_value()``, ``set_value()``, ``can_set()``, and ``get_default()`` methods that call the underlying Picam SDK functions. For example,

>>> cam.params.ShutterTimingMode.get_value()  #  => gives ShutterTimingMode.AlwaysOpen
>>> cam.params.ShutterTimingMode.set_value(PicamEnums.ShutterTimingMode.AlwaysClosed)
>>> cam.params.ShutterTimingMode.get_value()  #  verify the change


.. autoclass:: PicamCamera
   :members:


.. autoattribute:: instrumental.drivers.cameras.picam.PicamEnums


.. autoclass:: PicamError
   :members:


Picam Data Types
~~~~~~~~~~~~~~~~

These data types are returned by the API and are not meant to be created directly by users. They provide a wrapped interface to Picam's data types and automatically handle memory cleanup.

.. autoclass:: PicamCameraID
   :members:
   :exclude-members: __init__

.. autoclass:: PicamPulse
   :members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: PicamRois
   :members:
   :exclude-members: __init__

.. autoclass:: PicamRoi
   :members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: PicamModulations
   :members:
   :exclude-members: __init__

.. autoclass:: PicamModulation
   :members:
   :undoc-members:
   :exclude-members: __init__


Parameter Types
~~~~~~~~~~~~~~~

All Picam Parameters accessible through ``PicamCamera.params`` are instances of one of these classes.


.. autoclass:: IntegerParameter
   :members:
   :undoc-members:

.. autoclass:: LargeIntegerParameter
   :members:
   :undoc-members:

.. autoclass:: FloatingPointParameter
   :members:
   :undoc-members:

.. autoclass:: BooleanParameter
   :members:
   :undoc-members:

.. autoclass:: EnumerationParameter
   :members:
   :undoc-members:

.. autoclass:: ModulationsParameter
   :members:
   :undoc-members:

.. autoclass:: RoisParameter
   :members:
   :undoc-members:

.. autoclass:: PulseParameter
   :members:
   :undoc-members:

.. autoclass:: Parameter
   :exclude-members: __init__
 


Low Level Interface
~~~~~~~~~~~~~~~~~~~

The ``NicePicamLib`` class provides a more direct wrapping of the Picam SDK's C interface---what the NiceLib package calls a "Mid-level" interface. See the NiceLib documentation for more information on how to use this kind of interface.
