Installation
============

Brief Install Instructions
--------------------------

If you already have NumPy/SciPy/Matplotlib/pip installed, installing
Instrumental is simple. First install Pint::

    $ pip install pint

Now download and extract a zip of Instrumental from the `Github page
<https://github.com/mabuchilab/Instrumental>`_ or clone it using git. Now
install::

    $ cd /path/to/Instrumental
    $ python setup.py install
    $ python post_install.py

``post_install.py`` installs a config file, so you only have to run it the
first time you install Instrumental.


------------------------------------------------------------------------------


Detailed Install Instructions
-----------------------------

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
    $ python post_install.py
    
to install Instrumental to your Python site-packages directory and add a
default configuration to your config directory. You're all set! Now go check
out some of the examples in the ``examples`` directory contained in the files
you downloaded!

------------------------------------------------------------------------------

Optional Driver Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~

VISA
""""

.. ATTENTION::
    PyVISA is no longer required for talking to VISA devices if you have a
    FakeVISA server set up. Instead you should add the server address to your
    Instrumental config file. See details :ref:`here <fake-visa>`.

To operate devices that communicate using VISA, e.g. Tektronix scopes, you will
need::

1. an implementation of VISA, and
2. a Python interface layer called PyVISA
  
There are various implementations of VISA available, but two I know of are
TekVISA (from Tektronix) and NI-VISA (from National Instruments). They *should*
be compatible with each other, I believe the main difference is in the extra
vendor-specific utilities provided by each--either one should work fine with
PyVISA. Installers for each can be downloaded from the NI or Tektronix
websites, though you'll have to create a free account.

Once you've installed VISA, install PyVISA by running ``pip install pyvisa`` on
the command line. More info about PyVISA, including more detailed
install-related information can be found `here
<http://pyvisa.readthedocs.org/en/latest/>`_.


Thorlabs DCx Cameras
""""""""""""""""""""
To operate Thorlabs DCx cameras, you'll need the `drivers from Thorlabs
<http://www.thorlabs.us/software_pages/ViewSoftwarePage.cfm?Code=DCx>`_ under
the "Software and Support" tab. Run the .exe installer which, among other
things, will install the .dll shared libraries somewhere in your PATH
(hopefully). Currently the code only looks for the 64-bit driver, so if you're
on a 32-bit system I may need to work with you to fix this.


NI DAQs
"""""""
Currently, NI-DAQmx support requires `PyDAQmx
<https://pythonhosted.org/PyDAQmx/>`_. It can be installed via pip::

    $ pip install PyDAQmx

You will also need to have NI-DAQmx installed. You can find the installer
on the `National Instruments website <http://www.ni.com>`_.

Thorlabs CCSxxx Spectrometers
"""""""""""""""""""""""""""""

To operate a CCS spectrometer, you will need to install the `Thorlabs software
package 
<http://www.thorlabs.us/newgrouppage9.cfm?objectgroup_id=3482&pn=CCS100#3482>` 
under the software tab.  This should install the required .dll libraries in
your path.