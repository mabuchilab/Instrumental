Working with Instruments
========================

Getting Started
---------------

Instrumental tries to make it easy to find and open all the instruments
available to your computer. This is primarily accomplished using
``list_instruments()`` and ``instrument()``::

    >>> from instrumental import instrument, list_instruments
    >>> paramsets = list_instruments()
    >>> paramsets
    [<ParamSet[TSI_Camera] serial='05478' number=0>,
     <ParamSet[K10CR1] serial='55000247'>
     <ParamSet[NIDAQ] model='USB-6221 (BNC)' name='Dev1'>]

You can then use the output of ``list_instruments()`` to open the instrument you
want::

    >>> daq = instrument(paramsets[2])
    >>> daq
    <instrumental.drivers.daq.ni.NIDAQ at 0xb61...>

Or you can enter the parameters directly::

    >>> instrument(ni_daq_name='Dev1')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb61...>

If you're going to be using an instrument repeatedly, save it for later::

    >>> daq.save_instrument('myDAQ')

Then you can simply open it by name::

    >>> daq = instrument('myDAQ')


Using Units
~~~~~~~~~~~

``pint`` units are used heavily by Instrumental, so you should familiarize yourself with them. Many methods only accept unitful quantities, as a way to add clarity and prevent errors. In most cases you can use a string as shorthand and it will be converted automatically::

    >>> daq.ao1.write('3.14 V')

If you need to create your own quantities directly, you can use the ``u`` and ``Q_`` objects provided by Instrumental::

    >>> from instrumental import u, Q_

``u`` is a ``pint.UnitRegistry``, while ``Q_`` is a shorhand for the registry's ``Quantity`` class. There are several ways you can use them::

    >>> u.m                       # Access units as attributes
    <Unit('meter')>
    >>> 3 * u.s
    <Quantity(3, 'second')>

    >>> u('2.54 inches')          # Parse a string into a quantity using u()
    <Quantity(2.54, 'inch')>

    >>> Q('852 nm')               # ...or Q_()
    <Quantity(852, 'nanometer')>

    >>> Q(32.89, 'MHz')           # Specify magnitude and units separately
    <Quantity(32.89, 'megahertz')>

``pint`` also supports many physical constants (e.g. )

Note that it can be tricky to create offset units---e.g. by ``Q_('20 degC')``--- because ``pint`` treats this as a multiplication and will raise an ``OffsetUnitCalculusError``. You can get around this by separating the magnitude and units, e.g. ``Q_(20, 'degC')``. Note that ``Facets`` as well as the ``check_units`` and ``unit_mag`` decorators *can* properly parse strings like ``'20 degC'``.
 

Advanced Usage
--------------

An Even Quicker Way
~~~~~~~~~~~~~~~~~~~

Here's a shortcut for opening an instrument that means you don't have to assign the instrument list to a variable, or even know how to count---just use part of the instrument's string::

    >>> list_instruments()
    [<ParamSet[TSI_Camera] serial='05478' number=0>,
     <ParamSet[K10CR1] serial='55000247'>
     <ParamSet[NIDAQ] model='USB-6221 (BNC)' name='Dev1'>]
    >>> instrument('TSI')  # Opens the TSI_Camera
    >>> instrument('NIDAQ')  # Opens the NIDAQ

This will work as long as the string you use isn't saved as an instrument alias. If you use a
string that matches multiple instruments, it just picks the first in the list.


Filtering Results
~~~~~~~~~~~~~~~~~

If you're only interested in a specific driver or category of instrument, you can use the `module` argument to filter your results. This will also speed up the search for the instruments::

    >>> list_instruments(module='cameras')
    [<ParamSet[TSI_Camera] serial='05478' number=0>]
    >>> list_instruments(module='cameras.tsi')
    [<ParamSet[TSI_Camera] serial='05478' number=0>]

`list_instruments()` checks if ``module`` is a substring of each driver module's name. Only modules whose names match are queried for available instruments.


Remote Instruments
~~~~~~~~~~~~~~~~~~

You can even control instruments that are attached to a remote computer::

    >>> list_instruments(server='192.168.1.10')

This lists only the instruments located on the remote machine, not any local ones.

The remote PC must be running as an Instrumental server (and its firewall configured to allow
inbound connections on this port). To do this, run the script `tools/instr_server.py` that comes packaged
with Instrumental. The client needs to specify the server's IP address (or hostname), and port
number (if differs from the default of 28265). Alternatively, you may save an alias for this server
in the `[servers]` section of you `instrumental.conf` file (see :ref:`saved-instruments` for
more information about `instrumental.conf`). Then you can list the remote instruments like this::

    >>> list_instruments(server='myServer')

You can then open your instrument using `instrument()` as usual, but now you'll get a
`RemoteInstrument`, which you can control just like a regular `Instrument`.


How Does it All Work?
---------------------

Listing Instruments
~~~~~~~~~~~~~~~~~~~

What exactly is `list_instruments()` doing? Basically it walks through all the driver modules,
trying to import them one by one. If import fails (perhaps the DLL isn't available because the user
doesn't have this instrument), that module is skipped. Each module is responsible for returning a
list of its available instruments, e.g. the `drivers.daqs.ni` module returns a list of all the NI
DAQs that are accessible. ``list_instruments()`` combines all these instruments into one big list
and returns it.

There's an unfortunate side-effect of this: if a module fails to import due to a bug, the exception
is caught and ignored, so you don't get a helpful traceback. To diagnose issues with a driver
module, you can import the module directly::

    >>> import instrumental.drivers.daq.ni

or enable logging before calling `list_instruments()`::

    >>> from instrumental.log import log_to_screen
    >>> log_to_screen()


`list_instruments()` doesn't open instruments directly, but instead returns a list of dict-like `ParamSet` objects that contain info about how to open each instrument. For example, for our DAQ::

    >>> dict(paramsets[2])
    {'classname': 'NIDAQ',
     'model': 'USB-6221 (BNC)',
     'module': 'daq.ni',
     'name': 'Dev1',
     'serial': 20229473L}

We could also open it with keyword arguments::

    >>> instrument(name='Dev1')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb69...>

or a dictionary::

    >>> instrument({'name': 'Dev1'})
    <instrumental.drivers.daq.ni.NIDAQ at 0xb69...>

Behind the scenes, ``instrument()`` uses the keywords to figure out what type of instrument you're talking about, and what class should be instantiated. If you don't give it much information to use, it may take awhile scanning through the available instruments. You can speed this up by providing the model and/or classname::

    >>> instrument(module='daq.ni', classname='NIDAQ', name='Dev1')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb69...>

In addition, a convenient shorthand exists for specifying the module (or category of module) when you pass a parameter. For example::

    >>> instrument(ni_daq_name='Dev1')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb69...>

only looks at instrument types in the `daq.ni` module that have a `name` parameter. These special parameter names support the format ``<module>_<category>_<parameter>``, ``<module>_<parameter>``, and ``<category>_<parameter>``. The parameter name is split by underscores, then used to filter which modules are checked. Note that each segment can be abbreviated, so e.g. `cam_serial` will match all drivers in the `cameras` category having a `serial` parameter (this works because 'cam' is a substring of 'cameras').


.. _saved-instruments:

Saved Instruments
~~~~~~~~~~~~~~~~~

Opening instruments using `list_instruments()` is really helpful when you're messing around in the
shell and don't quite know what info you need yet, or you're checking what devices are available to
you. But if you've found your device and want to write a script that reuses it constantly, it's
convenient (and more efficient) to have it saved under an alias, which you can do easily with `save_instrument()` as we showed
above.

When you do this, the instrument's info gets saved in your `instrumental.conf` config file. To find
where the file is located on your system, run::

    >>> from instrumental.conf import user_conf_dir
    >>> user_conf_dir
    u'C:\\Users\\Lab\\AppData\\Local\\MabuchiLab\\Instrumental'

To save your instrument manually, you can add its parameters to the ``[instruments]`` section of `instrumental.conf`. For our DAQ, that would look like::

    # NI-DAQ device
    myDAQ = {'module': 'daq.ni', 'classname': 'NIDAQ', 'name': 'Dev1'}

This gives our DAQ the alias `myDAQ`, which can then be used to open it easily::

    >>> instrument('myDAQ')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb71...>

The default version of `instrumental.conf` also provides some commented-out example entries to help make things clear.


Reopen Policy
~~~~~~~~~~~~~

By default, Instrumental will prevent you from double-opening an instrument::

    >>> cam1 = instrument('myCamera')
    >>> cam2 = instrument('myCamera')  # results in an InstrumentExistsError

Usually it makes the most sense to simply reuse a previously-opened instrument rather than re-creating it. So, by default an exception is raised in if double-creation is attempted. However, this behavior is configurable via the ``reopen_policy`` parameter upon instrument creation.

::

    >>> cam1 = instrument('myCamera')
    >>> cam2 = instrument('myCamera', reopen_policy='reuse')
    >>> cam1 is cam2
    True

::

    >>> cam1 = instrument('myCamera')
    >>> cam2 = instrument('myCamera', reopen_policy='new')  # Might cause a driver error
    >>> cam1 is cam2
    False

The available policies are:

``strict``
    The default policy; raises an ``InstrumentExistsError`` if an ``Instrument`` object already exists that matches the given paramset.

``reuse``
    Returns the previously-created instrument object if it exists.

``new``
    Simply create the instrument as usual. Not recommended; only use this if you really know what you're doing, as the instrument driver is unlikely to support two objects controlling a single device.

For these purposes, an instrument "already exists" if the given paramset matches that of any ``Instrument`` which hasn't yet been garbage collected. Thus, an instrument *can* be re-created even under the ``strict`` policy as long as the old instrument has been fully deleted, either manually via ``del`` or automatically by it going out of scope.
