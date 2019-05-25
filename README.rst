.. image:: https://img.shields.io/travis/mabuchilab/Instrumental/master.svg
    :target: https://travis-ci.org/mabuchilab/Instrumental
    :alt: Travis CI

.. image:: https://img.shields.io/appveyor/ci/natezb/Instrumental/master.svg
    :target: https://ci.appveyor.com/project/natezb/instrumental
    :alt: AppVeyor CI

.. image:: https://img.shields.io/pypi/v/Instrumental-lib.svg
    :target: https://pypi.python.org/pypi/Instrumental-lib
    :alt: PyPI

.. image:: https://readthedocs.org/projects/instrumental-lib/badge/
   :target: https://instrumental-lib.readthedocs.io
   :alt: Documentation

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.2556399.svg
   :target: https://doi.org/10.5281/zenodo.2556399


|logo| Instrumental
===================

Instrumental is a Python-based library for controlling lab hardware like cameras, DAQs,
oscilloscopes, spectrometers, and more. It has high-level drivers for instruments from NI,
Tektronix, Thorlabs, PCO, Photometrics, Burleigh, and others.

Instrumental's goal is to make common tasks simple to perform, while still providing the
flexibility to perform complex tasks with relative ease. It also makes it easy to mess around with
instruments in the shell. For example, to list the available instruments and open one of them::

    >>> from instrumental import instrument, list_instruments
    >>> paramsets = list_instruments()
    >>> paramsets
    [<ParamSet[TSI_Camera] serial='05478' number=0>,
     <ParamSet[K10CR1] serial='55000247'>
     <ParamSet[NIDAQ] model='USB-6221 (BNC)' name='Dev1'>]
    >>> daq = instrument(paramsets[2])
    >>> daq
    <instrumental.drivers.daq.ni.NIDAQ at 0xb61...>

If you're going to be using an instrument repeatedly, save it for later::

    >>> daq.save_instrument('myDAQ')

Then you can simply open it by name::

    >>> daq = instrument('myDAQ')

Instrumental also bundles in some additional support code, including:

* Plotting and curve fitting utilities
* Utilities for acquiring and organizing data

Instrumental makes use of NumPy, SciPy, Matplotlib, and Pint, a Python units
library. It optionally uses PyVISA/VISA and other drivers for interfacing with
lab equipment.

For install information, documentation, examples, and more, see our page on
`ReadTheDocs <http://instrumental-lib.readthedocs.org/>`_.

.. |logo| image:: images/logo-small.png
          :alt: Instrumental

If you would like to cite Instrumental, to give it more visibility to other researchers, you can cite the repository through Zenodo (DOI: 10.5281/zenodo.2556399).
