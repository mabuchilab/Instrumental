Drivers
=======


Instrumental drivers allow you to control and read data from various hardware devices. The classes of devices currently supported include cameras, oscilloscopes, and function generators.

Some devices (e.g. Thorlabs cameras) have drivers that act as wrappers to their drivers' C bindings. Many others (e.g. Tektronix scopes and AFGs) utilize VISA and PyVISA, its python wrapper. PyVISA normally requires a local installation of the VISA library (e.g. TekVISA or NI-VISA) to interface with connected devices. Installing such a large package and making sure it's always running when you need it can be a pain. However, Instrumental provides its own module, named FakeVISA, that makes this process easier, and also enables easy remote access to VISA-compatible devices.


.. toctree::
    :maxdepth: 1

    cameras
    scopes
    funcgenerators
    powermeters
    wavemeters


-------------------------------------------------------------------------------


Functions
---------

.. automodule:: instrumental.drivers
    :members:

Example
~~~~~~~
    >>> from instrumental import instrument
    >>> scope = instrument('my_scope_alias')
    >>> x,y = scope.get_data()


-------------------------------------------------------------------------------

.. _fake-visa:

FakeVISA
--------

FakeVISA acts as a drop-in replacement for PyVISA, so you can easily use it with existing code. Only a small subset of PyVISA's functions are currently implemented, though they're probably all you need for the most common use cases. FakeVISA is implemented as a client running on your local machine that talks with a server script running on another machine that has PyVISA installed. The client relays commands to the server, which communicates them to the device and replies back with its response. This is especially simple since the VISA protocol primarily uses ASCII-encoded command strings.

FakeVISA works well, though it's still fairly experimental. Bug reports welcome! If demand exists, it could be possible to make a more general client-server protocol for communicating with all Instrumental-supported devices, rather than just those that are VISA-compatible.


Using the FakeVISA client
~~~~~~~~~~~~~~~~~~~~~~~~~
Once a FakeVISA server is running and the firewall's required ports are open, configuring the client should be straightforward. All you have to do is edit your Instrumental config file, ``instrumental.conf``.

First you probably want to add your FakeVISA servers to under the ``[servers]`` heading. Each entry is on its own line, with the format ``<alias> = <host or ip>:<port>``.

Then, under the ``[prefs]`` heading, set ``default_server`` to use the alias of the FakeVISA server you want to use (you can also use an ip:port combo directly rather than an alias if you prefer).


Running a FakeVISA server
~~~~~~~~~~~~~~~~~~~~~~~~~

To run the server script, you first need to have a VISA library installed. Search online for TekVISA, NI-VISA, or another vendor's implementation, and install the version for your system.

Next, install PyVISA. If you have pip_ installed (you should)::

    $ pip install pyvisa

To verify that everything's working, start up python and import PyVISA::

    >>> import visa
    >>> lib = visa.VisaLibrary()

Make sure that Instrumental is installed. In the `tools` subdirectory, there's a file called `server.py`. Run the script in a terminal to start the server::

    $ python server.py

TODO: Make the server script more robust and configurable (i.e. automatically get the ip address right). Also, let it run in the background and add instructions for running it on start-up, etc.

.. _pip: http://www.pip-installer.org/


