VISA Driver Example
===================

In this guide, we'll run through the process of making a VISA-based driver using the example of a Thorlabs PM100D power meter.

If you're following along, it may be helpful to look at the PM100D's commands, listed in the "SCPI Commands" section of its `manual [PDF]`_.

.. _manual [PDF]: https://www.thorlabs.com/_sd.cfm?fileName=17654-D02.pdf&partNumber=PM100D

First, let's open the device and play around with it in an ipython shell using pyvisa:

.. code-block:: ipython

    In [1]: import visa

    In [2]: rm = visa.ResourceManager()

    In [4]: rm.list_resources()
    Out[4]:
    (u'USB0::0x1313::0x8078::P0009084::INSTR',
     u'USB0::0x0699::0x0362::C101689::INSTR',
     u'ASRL1::INSTR',
     u'ASRL3::INSTR')


Which resource is our power meter? Well, like all well-behaved SCPI instruments, the PM100D supports the ``*IDN?`` command, which asks the device to identify itself. Let's query the IDN of each of these resources:

.. code-block:: ipython

    In [5]: for addr in rm.list_resources():
       ...:     try:
       ...:         print(addr, '-->', rm.open_resource(addr).query('*IDN?').strip())
       ...:     except visa.VisaIOError:
       ...:         pass
       ...:

    USB0::0x1313::0x8078::P0009084::INSTR --> Thorlabs,PM100D,P0009084,2.4.0
    USB0::0x0699::0x0362::C101689::INSTR --> TEKTRONIX,TDS 1001B,C101689,CF:91.1CT FV:v22.11


We've used a try-except block here to catch errors from any devices that don't support the ``*IDN?`` command. We can now see which device is our power meter. Let's open it and try some of the commands listed in the manual:

.. code-block:: ipython

    In [5]: rsrc = rm.open_resource('USB0::0x1313::0x8078::P0009084::INSTR',
                                    read_termination='\n')

    In [6]: rsrc.query('measure:power?')
    Out[6]: '4.20021615E-06'

    In [7]: rsrc.query('power:dc:unit?')
    Out[7]: 'W'

    In [8]: rsrc.query('sense:corr:wav?')
    Out[8]: '8.520000E+02'

Here we've set the resource's read termination to automatically strip off the newline at the end of each message, to make the output clearer. We can see that our power meter is measuring 4.2 microwatts of optical power and its operation wavelength is set to 852 nm. Let's change the wavelength:

.. code-block:: ipython

    In [9]: rsrc.write('sense:corr:wav 532')
    Out[9]: (20, <StatusCode.success: 0>)

    In [10]: rsrc.query('sense:corr:wav?')
    Out[10]: '5.320000E+02'


Now let's get start writing our driver::

    from instrumental.drivers.powermeters import PowerMeter
    from instrumental.drivers import VisaMixin

    class PM100D(PowerMeter, VisaMixin):
        """A Thorlabs PM100D series power meter"""
        _INST_PARAMS_ = ['visa_address']


We inherit from ``PowerMeter``, a subclass of ``Instrument``, and use the ``_INST_PARAMS_`` class attribute to declare what parameters our instrument needs. We also inherit from ``VisaMixin``, a mixin class which provides us some useful VISA-related features:

.. code-block:: ipython

    In [1]: from mydriver import *

    In [2]: pm = PM100D(visa_address='USB0::0x1313::0x8078::P0009084::INSTR')

    In [3]: pm.resource
    Out[3]: <'USBInstrument'(u'USB0::0x1313::0x8078::P0009084::INSTR')>

    In [4]: pm.query('*IDN?')
    Out[4]: 'Thorlabs,PM100D,P0009084,2.4.0\n'


``VisaMixin`` allows us to construct an instance by providing only a ``visa_address`` parameter, and provides our class with a ``resource`` attribute as well as ``query`` and ``write`` convenience methods. Notice that the message termination isn't being stripped. We can enable this by setting ``read_termination`` inside the ``_initialize`` method, which is called just after the instance is created::

    from instrumental.drivers.powermeters import PowerMeter
    from instrumental.drivers import VisaMixin

    class PM100D(PowerMeter, VisaMixin):
      """A Thorlabs PM100D series power meter"""
      def _initialize(self):
          self.resource.read_termination = '\n'


Now let's add a method to return the measured optical power::

    from instrumental import Q_
    [...]
    class PM100D(PowerMeter, VisaMixin):
      def power(self):
          """The measured optical power"""
          self.write('power:dc:unit W')
          power_W = float(self.query('measure:power?'))
          return Q_(power_W, 'W')

This will sets the measurement units to watts, queries the power, and returns it as a unitful ``Quantity``. Let's try it out:

.. code-block:: ipython

    In [3]: pm.power()
    Out[3]: <Quantity(1.03476232e-05, 'watt')>


Now let's add a way to get and set the wavelength, but let's use the ``SCPI_Facet`` convenience function, which allows us to concisely wrap well-behaving SCPI commands::

    from instrumental.drivers import VisaMixin, SCPI_Facet
    [...]
    class PM100D(PowerMeter, VisaMixin):
        [...]
        wavelength = SCPI_Facet('sense:corr:wav', units='nm', type=float,
                                doc="Input signal wavelength")

``wavelength`` here is a ``Facet``, which is like a suped-up python ``property``. We've told ``SCPI_Facet`` the command to use, and noted that it refers to a float with units of nanometers. Now we let's see how our new wavelength attribute behaves:

.. code-block:: ipython

    In [4]: pm.wavelength
    Out[4]: <Quantity(532.0, 'nanometer')>

    In [5]: pm.wavelength = 1064
    [...]
    DimensionalityError: Cannot convert from 'dimensionless' (dimensionless) to 'nanometer' ([length])


What happened? The Facet ensures that we set the wavelength in units of length, to keep us from making unit conversion errors. We can use either a Quantity or a string that can be parsed by ``Q_()``

.. code-block:: ipython

    In [6]: pm.wavelength = Q_(1064, 'nm')

    In [7]: pm.wavelength
    Out[7]: <Quantity(1064.0, 'nanometer')>

    In [8]: pm.wavelength = Q_(0.633, 'um')

    In [9]: pm.wavelength
    Out[9]: <Quantity(633.0, 'nanometer')>

    In [10]: pm.wavelength = '852 nm'

    In [11]: pm.wavelength
    Out[11]: <Quantity(852.0, 'nanometer')>


That's better. Now that we have a basic driver, we need to make sure everything is cleaned up when we close our instrument. For most VISA-based instruments, this isn't necessary, but the PM100D enters a special REMOTE mode, which locks out the front panel, when you start sending it commands. We use the ``control_ren()`` method of ``pyvisa.resources.USBInstrument`` to disable remote mode::

    [...]
    class PM100D(PowerMeter, VisaMixin):
        [...]
        def close(self):
            self.resource.control_ren(False)  # Disable remote mode


The ``close()`` method can be called explicitly, and it is automatically called when the instrument is cleaned up or the interpreter exits. This way, the power meter will exit remote mode even if our program exits due to an exception.


::

    @Facet(units='W', cached=False)
    def power(self):
        """The measured optical power"""
        self.write('power:dc:unit W')
        return float(self.query('measure:power?'))

::

    from instrumental.drivers.powermeters import PowerMeter
    from instrumental.drivers import Facet, SCPI_Facet, VisaMixin, deprecated
    class PM100D(PowerMeter, VisaMixin):
        """A Thorlabs PM100D series power meter"""
        range = SCPI_Facet('power:dc:range', units='W', convert=float, readonly=True,
                           doc="The current input range's max power")

        auto_range = SCPI_Facet('power:dc:range:auto', convert=int, value={False:0, True:1},
                                doc="Whether auto-ranging is enabled")

        wavelength = SCPI_Facet('sense:corr:wav', units='nm', type=float,
                                doc="Input signal wavelength")

        num_averaged = SCPI_Facet('sense:average:count', type=int,
                                  doc="Number of samples to average")

        def close(self):
            self._rsrc.control_ren(False)  # Disable remote mode

