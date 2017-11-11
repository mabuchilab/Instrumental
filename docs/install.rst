Installation
============

Brief Install Instructions
--------------------------

Starting with version 0.2.1, you can install Instrumental using pip::

    $ pip install instrumental-lib

This will install the latest release version along with the core dependencies if they aren't
already installed. However, it's recommended that you use the the Anaconda distribution so you
don't have to compile numpy and scipy (see the detailed install instructions below).


Installing the Development Version from GitHub
----------------------------------------------

Once you have the core dependencies installed (numpy, scipy, and pint), download and extract a zip
of Instrumental from the `Github page <https://github.com/mabuchilab/Instrumental>`_ or clone it
using git. Now install::

    $ cd /path/to/Instrumental
    $ python setup.py install

------------------------------------------------------------------------------


Detailed Install Instructions
-----------------------------

Instrumental should install any core dependencies it requires, but if you're having problems, you may want to read this section over. Note that many *per-driver* dependencies are not installed automatically, so you can install them as-needed.


Python Sci-Comp Stack
~~~~~~~~~~~~~~~~~~~~~
To install the standard scientific computing stack, I recommend using `Anaconda
<http://continuum.io/downloads>`_. Download the appropriate installer from the
download page and run it to install Anaconda. The default installation will
include NumPy, SciPy, and Matplotlib as well as lots of other useful stuff.

Pint
~~~~
Next, install Pint for units support:: 

    $ pip install pint

For more information, or to get a more recent version, check out the `Pint
install page <https://pint.readthedocs.org/en/latest/getting.html>`_.


Instrumental
~~~~~~~~~~~~
If you're using git, you can clone the Instrumental repository to get the
source code. If you don't know git or don't want to set up a local repo yet,
you can just download a zip file by clicking the 'Download ZIP' button on the
right hand side of the `Instrumental Github page
<https://github.com/mabuchilab/Instrumental>`_.  Unzip the code wherever you'd
like, then open a command prompt to that directory and run::

    $ python setup.py install
    
to install Instrumental to your Python site-packages directory.  You're all set! Now go check out
some of the examples in the ``examples`` directory contained in the files you downloaded!

------------------------------------------------------------------------------

Optional Driver Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~

VISA
""""

To operate devices that communicate using VISA (e.g. Tektronix scopes) you will
need:

1. an implementation of VISA, and
2. a Python interface layer called PyVISA
  
There are various implementations of VISA available, but two I know of are
TekVISA (from Tektronix) and NI-VISA (from National Instruments). I would
recommend NI-VISA, though either one should work fine. Installers for each can
be downloaded from the NI or Tektronix websites, though you'll have to create a
free account.

Once you've installed VISA, install PyVISA by running::

    $ pip install pyvisa

on the command line. As a quick test PyVISA has installed correctly, open a
python interpreter and run::

    >>> import visa
    >>> rm = visa.ResourceManager()
    >>> rm.list_resources()

More info about PyVISA, including more detailed install-related information can
be found `here <http://pyvisa.readthedocs.org/en/latest/>`_.



Thorlabs DCx Cameras
""""""""""""""""""""
To operate Thorlabs DCx cameras, you'll need the `drivers from Thorlabs
<http://www.thorlabs.us/software_pages/ViewSoftwarePage.cfm?Code=DCx>`_ under the "Software and
Support" tab. Run the .exe installer which, among other things, will install the .dll shared
libraries somewhere in your PATH (hopefully).

NI DAQs
"""""""
NI-DAQmx support requires you to to have NI-DAQmx installed. You can find the installer on the
`National Instruments website <http://www.ni.com>`_.
