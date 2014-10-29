Working with Instruments
========================

Getting Started
---------------

Instrumental tries to make it easy to find and open all the instruments
available to your computer. This is primarily accomplished using
``list_instruments()`` and ``instrument()``::

    >>> from instrumental import instrument, list_instruments
    >>> insts = list_instruments()
    >>> insts
    [<TEKTRONIX 'DPO4034'>, <TEKTRONIX 'MSO4034'>, <NIDAQ 'Dev1'>]

You can then use the output of ``list_instruments()`` to open the instrument you
want::

    >>> daq = instrument(insts[2])
    >>> daq
    <instrumental.drivers.daq.ni.NIDAQ at 0xb61...>

How does this work? Well, ``list_instruments()`` returns a list of
dictionary-like elements that contain info about how to open the instrument.
For example, for our DAQ::

    >>> dict(insts[2])
    {u'nidaq_devname': u'Dev1'}

This tells us that the daq is uniquely identified by the parameter
`nidaq_devname`. So, we could also open it with keyword arguments::

    >>> instrument(nidaq_devname='Dev1')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb69...>

or a dictionary::

    >>> instrument({'nidaq_devname': 'Dev1'})
    <instrumental.drivers.daq.ni.NIDAQ at 0xb62...>

Behind the scenes, ``instrument()`` uses the keywords to figure out what type
of instrument you're talking about, and what class should be instantiated.


Using Saved Instruments
-----------------------

Opening instruments this way is really helpful when you're messing around in
the shell and don't quite know what info you need yet, or you're checking what
devices are available to you. But if you've found your device and want to write
a script that reuses it constantly, it's nice to have it saved in your
`instrumental.conf` config file. To find where the file is located on your
system, run::

    >>> from instrumental.conf import data_dir
    >>> data_dir
    u'C:\\Users\\Lab\\AppData\\Local\\MabuchiLab\\Instrumental'

To save your instrument for repeated use, add its parameters to the ``[instruments]``
section of `instrumental.conf`. For our DAQ, that would look like::

    # NI-DAQ device
    myDAQ = {'nidaq_devname': 'Dev1'}

This gives our DAQ the alias `myDAQ`, which can then be used to open it easily::

    >>> instrument('myDAQ')
    <instrumental.drivers.daq.ni.NIDAQ at 0xb71...>

The default version of `instrumental.conf` also provides some commented-out
example entries to help make things clear.
