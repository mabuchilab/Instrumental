Installation
============

Brief Install Instructions
--------------------------

If you already have NumPy/SciPy/Matplotlib/pip installed, installing Instrumental is simple. First install Pint::

    $ pip install pint

Now download and extract a zip of Instrumental from the `Github page <https://github.com/mabuchilab/Instrumental>`_ or clone it using git. Now install::

    $ cd /path/to/Instrumental
    $ python setup.py install
    $ python post_install.py

``post_install.py`` installs a config file, so you only have to run it the first time you install Instrumental.


Detailed Install Instructions
-----------------------------

Python Sci-Comp Stack
~~~~~~~~~~~~~~~~~~~~~
To install the standard scientific computing stack, I recommend using `Anaconda <http://continuum.io/downloads>`_. Download the appropriate installer from the download page and run it to install Anaconda. The default installation will include NumPy, SciPy, and Matplotlib as well as lots of other useful stuff.

Pint
~~~~
Next, install Pint for units support:: 

    $ pip install pint

For more information, or to get a more recent version, check out the `Pint install page <https://pint.readthedocs.org/en/latest/getting.html>`_.

VISA (optional)
~~~~~~~~~~~~~~~

.. ATTENTION::
    PyVISA is no longer required for talking to VISA devices. Instead you should add a server address to your Instrumental config file. See details :ref:`here <fake-visa>`.

To operate devices that communicate using VISA, e.g. Tektronix scopes, you will need (1) an implementation of VISA and (2) a Python interface layer called PyVISA. There are various implementations of VISA available, but two I know of are TekVISA (from Tektronix) and NI-VISA (from National Instruments). They *should* be compatible with each other, I believe the main difference is in the extra vendor-specific utilities provided by each--either one should work fine with PyVISA. Installers for each can be found on the lab's shared drive under "labusers/common/Software Downloads/VISA", or you can get them from the NI or Tektronix websites, though you'll have to create a free account.

Once you've installed VISA, install PyVISA by running ``pip install pyvisa`` on the command line. More info about PyVISA, including more detailed install-related information can be found `here <http://pyvisa.readthedocs.org/en/latest/>`_.

Thorlabs DCx Cameras (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To operate Thorlabs DCx cameras, you'll need the `drivers from Thorlabs <http://www.thorlabs.us/software_pages/ViewSoftwarePage.cfm?Code=DCx>`_ under the "Software and Support" tab. Run the .exe installer which, among other things, will install the .dll shared libraries somewhere in your PATH (hopefully). Currently the code only looks for the 64-bit driver, so if you're on a 32-bit system I may need to work with you to fix this.

Instrumental
~~~~~~~~~~~~
If you're using git, you can clone the Instrumental repository to get the source code. If you don't know git or don't want to set up a local repo yet, you can just download a zip file by clicking the 'Download ZIP' button on the right hand side of the `Instrumental Github page <https://github.com/mabuchilab/Instrumental>`_. Those without private Github access can download the zip file `here <http://stanford.edu/group/mabuchilab/files/Instrumental.zip>`_. Unzip the code wherever you'd like, then open a command prompt to that directory and run::

    $ python setup.py install
    $ python post_install.py
    
to install Instrumental to your Python site-packages directory and add a default configuration to your config directory. You're all set! Now go check out some of the examples in the ``examples`` directory contained in the files you downloaded!

