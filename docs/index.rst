.. image:: ../images/logo.png
    :align: right

Instrumental
============

Instrumental is a Python-based library of support code used by the Mabuchi Lab
at Stanford University. It consists of:

* High-level drivers for controlling common lab equipment
* Plotting and curve fitting utilities
* Tools for working with optics, including Gaussian beams and ABCD matrices
* Utilities for acquiring and organizing data

Instrumental makes use of NumPy, SciPy, Matplotlib, and Pint, a Python units
library. It optionally uses PyVISA/VISA and other drivers for interfacing with
lab equipment.

To download Instrumental or browse its source, see our `GitHub page
<https://github.com/mabuchilab/Instrumental>`_.

.. NOTE::
    Instrumental is currently still under heavy development, so its interfaces
    are subject to change. Contributions are greatly appreciated, see the
    :doc:`developer` for more info.


User Guide
----------

.. toctree::
   :maxdepth: 2

   install
   overview
   quickstart
   api
   developer
