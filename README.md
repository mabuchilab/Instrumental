![logo] Instrumental
====================

Instrumental is a Python-based instrumentation library (and more!) for the Mabuchi Lab.

It currently serves as a repository for some useful code and is organized into four primary modules: drivers, plotting, fitting, and tools. The organization of code is almost certainly suboptimal for now, so everything is subject to change as the library grows.

Instrumental makes heavy use of the scientific libraries NumPy, SciPy, and Matplotlib, as well as (optional?) integration of Pint, a Python units library.

Drivers
-------
This module's purpose is to provide relatively high-level 'drivers' for interfacing with our lab equipment. Currently it supports:
-   Tektronix TDS3032 Digital Oscilloscopes
-   Thorlabs DCx class USB cameras
It should be pretty easy to write drivers for other Tektronix scopes (and anything else that uses VISA) via PyVisa. Driver submissions are greatly appreciated!


Plotting
--------
This module provides or aims to provide
-   Unit-aware (Pint-aware) plotting functions
-   Easy slider-plots
-   Curated 'nice' default settings/colors/etc for both data analysis and publication/figures


Fitting
-------
This module is a good place for curating 'standard' lab-wide fits for common cases like
-   Triple-lorentzian cavity scans
-   Ringdown traces (exponential decay)

It should also provide optional unit-awareness.


Tools
-----
The tools module is used for full-fledged scripts and programs that may make use of all of the other modules above. A good example would be a script that pulls a trace from the scope, auto-fits a ringdown curve, and saves both the raw data and fit parameters to files in a well-organized directory structure.

[logo]: images/logo.png "Instrumental"
