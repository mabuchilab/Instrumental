Driver Parameters
-----------------
Parameters are at the heart of ``instrument()`` and ``list_instruments()``. ``'module'`` is a special parameter name, which indicates that the driver can open an instrument without requiring any params (i.e. you need only know the appropriate module). This allows you to provide support for returning the first available device.

You can customize how an instrument's paramset is filled out by overriding the ``_fill_out_paramset`` method. The default implementation uses ``list_instruments`` to find a matching paramset, and updates the original paramset with any fields that are missing.

This paramset is the ``_paramset`` attribute of each instrument.


Special params
""""""""""""""
There are a few parameters that are treated specially. These include:

module
    The name of the driver module, relative to the `drivers` package, e.g. `scopes.tektronix`.
classname
    The name of the class to which these parameters apply.
server
    The address of an instrument server which should be used to open the remote instrument.
settings
    A dict of extra settings which get passed as arguments to the instrument's constructor. These settings are separated from the other parameters because they are not considered *identifying information*, but simply configuration information. More specifically, changing the `settings` should never change which instrument the given `Params` will open.
visa_address
    The address string of a VISA instrument. If this is given, Instrumental will assume the parameters refer to a VISA instrument, and will try to open it with one of the VISA-based drivers.

Common params
"""""""""""""
Driver-defined parameters can be named pretty much anything (other than the special names given above). However, they should typically fall into a small set of commonly shared names to make the user's life easier. Some commonly-used names you should consider using include:

- serial
- model
- number
- id
- name
- port

In general, don't use vendor-specific names like `newport_id` (also avoid including underscores, for reasons that will become clear). Convenient vendor-specific parameters are automatically supported by `instrument()`. Say for example that the driver `cameras.tsi` supports a `serial` parameter. Then you can use any of the parameters `serial`, `tsi_serial`, `tsi_camera_serial`, and `camera_serial` to open the camera. The parameter name is split by underscores, then used to filter which modules are checked.

Note that `camera_serial` (vs `cameras_serial`) is not a typo. Each section is matched by substring, so you can even use something like `tsi_cam_ser`.
