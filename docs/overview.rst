Overview
========

.. _driver-list:

Drivers
-------
The ``drivers`` subpackage is the primary focus of Instrumental, and its purpose is to provide relatively high-level 'drivers' for interfacing with lab equipment. Currently it (fully or partially) supports:

* Cameras

  - PCO SDK (tested on PCO.Edge)
  - PCO Pixelfly
  - Photometrics PVCAM
  - Thorlabs TSI
  - Thorlabs UC480 / iDS uEye

* DAQs

  - NI-DAQmx

* Function Generators

  - Tektronix AFG3000 series

* Lasers

  - Toptica FemtoFErb 1560

* Lock-in Amplifiers

  - SRS SR850

* Motion Control

  - Thorlabs Kinesis (FilterFlipper/TDC001/K10CR1 currently supported)
  - Attocube ECC100 Controller

* Multimeters

  - HP 34401A

* Optical Power Meters

  - Newport 1830-C
  - Thorlabs PM100x series

* Oscilloscopes

  - Tektronix TDS300 and MSO/DPO4000 series (and probably others)

* Spectrometers

  - Bristol 721 spectrum analyzer
  - Thorlabs CCSxxx series

* Wavemeters

  - Burleigh WA-1000/1500

It should be pretty easy to write drivers for other VISA-compatible devices by using `VisaMixin` and `Facets`. Check out :doc:`driver-dev` for more info. Driver submissions are greatly appreciated!


-------------------------------------------------------------------------------

Other Subpackages
-----------------
There are several other subpackages within Instrumental. These may eventually be moved to their own separate packages.


Plotting
""""""""
The ``plotting`` module provides or aims to provide

* Unit-aware plotting functions as a drop-in replacement for pyplot
* Easy slider-plots


Fitting
"""""""
The ``fitting`` module is a good place for curating 'standard' fitting tools
for common cases like

* Triple-lorentzian cavity scans
* Ringdown traces (exponential decay)

It should also provide optional unit-awareness.


Tools
"""""
The ``tools`` module is used for full-fledged scripts and programs that may
make use of all of the other modules above. A good example would be a script
that pulls a trace from the scope, auto-fits a ringdown curve, and saves both
the raw data and fit parameters to files in a well-organized directory
structure.
