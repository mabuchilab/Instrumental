Installation
============

.. contents::
    :local:
    :depth: 2


Brief Install Instructions
--------------------------

Simply install Instrumental from PyPI using pip::

    $ pip install instrumental-lib

This will install the latest release version along with the core dependencies if they aren't already
installed.

Installing the Development Version from GitHub
----------------------------------------------

Download and extract a zip of Instrumental from the `Github page
<https://github.com/mabuchilab/Instrumental>`_ or clone it using git. Now install::

    $ cd /path/to/Instrumental
    $ python setup.py install

------------------------------------------------------------------------------


Optional Driver Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~

VISA
""""
To operate devices that communicate using VISA (e.g. Tektronix scopes) you will
need:

1. an implementation of VISA, and
2. a Python interface layer called PyVISA

More info about PyVISA, including more detailed install-related information can
be found `here <http://pyvisa.readthedocs.org/en/latest/>`_.


Other Drivers
"""""""""""""
Install directions are located on each driver's page within the :doc:`drivers` section. This
lists the python packages that are required, as well as any external libraries.
