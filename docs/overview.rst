Overview
========

Drivers
-------
The ``drivers`` subpackage's purpose is to provide relatively high-level 'drivers' for interfacing with our lab equipment. Currently it supports:

-   Many Tektronix Digital Oscilloscopes
-   Thorlabs DCx class USB cameras

It should be pretty easy to write drivers for other Tektronix scopes (and anything else that uses VISA) via PyVISA. Driver submissions are greatly appreciated!


Plotting
--------
The ``plotting`` module provides or aims to provide

-   Unit-aware (Pint-aware) plotting functions
-   Easy slider-plots
-   Curated 'nice' default settings/colors/etc for both data analysis and publication/figures


Fitting
-------
The ``fitting`` module is a good place for curating 'standard' lab-wide fits for common cases like

-   Triple-lorentzian cavity scans
-   Ringdown traces (exponential decay)

It should also provide optional unit-awareness.


Tools
-----
The ``tools`` module is used for full-fledged scripts and programs that may make use of all of the other modules above. A good example would be a script that pulls a trace from the scope, auto-fits a ringdown curve, and saves both the raw data and fit parameters to files in a well-organized directory structure.

