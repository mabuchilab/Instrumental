Overview
========

Drivers
-------
The ``drivers`` subpackage's purpose is to provide relatively high-level
'drivers' for interfacing with lab equipment. Currently it (fully or partially)
supports:

* Tektronix TDS300 and MSO/DPO4000 series oscilloscopes
* Tektronix AFG3000 series arbitrary function generators
* Thorlabs DCx class USB cameras
* NI DAQmx compatible DAQ devices
* Attocube ECC100 controller and associated translation stages and
  goniometers

Drivers are planned for:

* Thorlabs PM100x series optical power meters
* Newport 1830-C optical power meter
* Thorlabs APT motion control systems (e.g. T-Cube motor controllers)

It should be pretty easy to write drivers for other VISA-compatible devices via PyVISA. Driver submissions are greatly appreciated!


-------------------------------------------------------------------------------


Plotting
--------
The ``plotting`` module provides or aims to provide

* Unit-aware plotting functions as a drop-in replacement for pyplot
* Easy slider-plots


-------------------------------------------------------------------------------


Fitting
-------
The ``fitting`` module is a good place for curating 'standard' fitting tools
for common cases like

* Triple-lorentzian cavity scans
* Ringdown traces (exponential decay)

It should also provide optional unit-awareness.


-------------------------------------------------------------------------------


Optics
------

The ``optics`` module is a repository for useful optics code. Currently it
focuses on using numerical ABCD matrices to manipulate and visualize paraxial
gaussian beams. For example, it can be used to easily specify the elements of
an optical cavity, solve for the supported modes, and plot the tangential and
sagittal spot size throughout the beam path.

-------------------------------------------------------------------------------

Tools
-----
The ``tools`` module is used for full-fledged scripts and programs that may
make use of all of the other modules above. A good example would be a script
that pulls a trace from the scope, auto-fits a ringdown curve, and saves both
the raw data and fit parameters to files in a well-organized directory
structure.
