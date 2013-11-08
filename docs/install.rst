Instrumental
============

Instrumental is a Python-based instrumentation library (and more!) for the Mabuchi Lab.

It currently serves as a repository for some useful code and is organized into four primary parts: drivers, plotting, fitting, and tools. The organization of code is almost certainly suboptimal for now, so everything is subject to change as the library grows.

Instrumental makes heavy use of the scientific libraries NumPy, SciPy, and Matplotlib, as well as (optional?) integration of Pint, a Python units library, and PyVISA, VISA, and other drivers for interfacing with lab devices.


Installation
------------
Most of Instrumental depends on the standard Python scientific computing stack of Python, NumPy, SciPy, and Matplotlib. Additionally, it makes use of the Pint units library as well as optional driver software for communicating with lab hardware.

Python Sci-Comp Stack
~~~~~~~~~~~~~~~~~~~~~
To install the standard scientific computing stack, I recommend using `Anaconda <http://continuum.io/downloads>`_. Download the appropriate installer from the download page and run it to install Anaconda. The default installation will include NumPy, SciPy, and Matplotlib.

Pint (optional)
~~~~~~~~~~~~~~~
Next, install Pint for units support. This is optional, but highly recommended, as some of Instrumental's code currently relies on Pint. To install Pint, simply open up a terminal and run `pip install pint`. For more information, or to get a more up-to-date version of Pint, check out the `Pint install page <https://pint.readthedocs.org/en/latest/getting.html>`_.

VISA (optional)
~~~~~~~~~~~~~~~
To operate devices that communicate using VISA, e.g. Tektronix scopes, you will need (1) an implementation of VISA and (2) a Python interface layer called PyVISA. There are various implementations of VISA available, but two I know of are TekVISA (from Tektronix) and NI-VISA (from National Instruments). They *should* be compatible with each other, I believe the main difference is in the extra vendor-specific utilities provided by each--either one should work fine with PyVISA. Installers for each can be found on the lab's shared drive under "labusers\common\Software Downloads\VISA", or you can get them from the NI or Tektronix websites, though you'll have to create a free account. Once you've installed VISA, install PyVISA by running `pip install pyvisa` on the command line. More info about PyVISA, including more detailed install-related information can be found `here <http://pyvisa.readthedocs.org/en/latest/>`_.

Thorlabs DCx Cameras (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Finally, to operate Thorlabs DCx cameras, you'll need the drivers from `Thorlabs <http://www.thorlabs.us/software_pages/ViewSoftwarePage.cfm?Code=DCx>`_ under the "Software and Support" tab. Run the .exe installer which, among other things, will install the .dll shared libraries somewhere in your PATH (hopefully). Currently my code only looks for the 64-bit driver, so if you're on a 32-bit system I may need to work with you to fix this.

Instrumental
~~~~~~~~~~~~
If you experience with git, you can clone the Instrumental repository to get the source code. If you don't know git or don't want to set up a local repo yet, you can just download a zip file by clicking the 'Download ZIP' button on the right hand side of the `Instrumental Github page <https://github.com/mabuchilab/Instrumental>`_. Those without private Github access can download the zip file `here <http://stanford.edu/group/mabuchilab/files/Instrumental.zip>`_. Unzip the code wherever you'd like, then open a command prompt to that directory and run `python setup.py install` to install Instrumental to your Python site-packages directory. You're all set! Now go check out some of the examples in the `examples` directory contained in the files you downloaded!


Subpackages and Modules
-----------------------

Drivers
~~~~~~~
The `drivers` subpackage's purpose is to provide relatively high-level 'drivers' for interfacing with our lab equipment. Currently it supports:
-   Tektronix TDS3032 Digital Oscilloscopes
-   Thorlabs DCx class USB cameras
It should be pretty easy to write drivers for other Tektronix scopes (and anything else that uses VISA) via PyVisa. Driver submissions are greatly appreciated!


Plotting
~~~~~~~~
The `plotting` module provides or aims to provide
-   Unit-aware (Pint-aware) plotting functions
-   Easy slider-plots
-   Curated 'nice' default settings/colors/etc for both data analysis and publication/figures


Fitting
~~~~~~~
The `fitting` module is a good place for curating 'standard' lab-wide fits for common cases like
-   Triple-lorentzian cavity scans
-   Ringdown traces (exponential decay)

It should also provide optional unit-awareness.


Tools
~~~~~
The `tools` module is used for full-fledged scripts and programs that may make use of all of the other modules above. A good example would be a script that pulls a trace from the scope, auto-fits a ringdown curve, and saves both the raw data and fit parameters to files in a well-organized directory structure.

