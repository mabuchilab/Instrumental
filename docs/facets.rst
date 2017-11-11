Facets
======

.. NOTE::
   Facets are new in version 0.4

A ``Facet`` represents an attribute (or facet) of an instrument. For example, the wavelength setting on an optical power meter. Facets exist to make drivers easier to write, provide a more consistent interface, and provide more advanced features like unit conversion and bounds-checking. They also make driver code more declarative, and hence easier to read. Take, for example, this snippet from the Thorlabs PM100D driver::

    class PM100D(PowerMeter, VisaMixin):
        """A Thorlabs PM100D series power meter"""

        wavelength = SCPI_Facet('sense:corr:wav', units='nm', type=float,
                                doc="Input signal wavelength")

This is very little code, yet it already gives us something pretty useful. Let's say we open such a power meter, named `pm`::

    >>> pm.wavelength
    <Quantity(852.0, 'nanometer')
    >>> pm.wavelength = '532 nm'
    >>> pm.wavelength
    <Quantity(532.0, 'nanometer')
    >>> pm.wavelength = 1064
    DimensionalityError: Cannot convert from 'dimensionless' to 'nanometer'

As you can see, the facet automatically parses and checks units, and converts any ints to floats. We could also specify the allowed wavelength range if we wanted to.

``SCPI_Facet`` is a helper function for creating facets for devices that follow SCPI messaging standards. When we enter `pm.wavelength`, it sends the message `sense:corr:wav?` to the device, reads its response, and converts it into the proper type and units. Similarly, when we enter `pm.wavelength = '532 nm'`, it sends the `sense:corr:wav 532` to the device.

If you're using a message-based device with slightly different message format, it's easy to write your own wrapper function that calls `MessageFacet`. Check out the source of `SCPI_Facet` to see how this is done. It's frequently useful to write a helper function like this for a given driver, even if it's not message-based.


.. autoclass:: instrumental.drivers.Facet
.. autofunction:: instrumental.drivers.MessageFacet
.. autofunction:: instrumental.drivers.SCPI_Facet
