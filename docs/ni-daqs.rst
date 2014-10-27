NI DAQs
=======

.. toctree::

This module has been developed using an NI USB-6221 -- the code should generally work for all DAQmx boards, but I'm sure there are plenty of compatibility bugs just waiting for you wonderful users to find and fix.

First, make sure you have NI's DAQmx software installed. Once that's set, you'll need PyDAQmx, a basic Python interface to DAQmx. You can get it via pip::

    pip install PyDAQmx

The `NIDAQ` class lets you interact with your board and all its various inputs
and outputs in a fairly simple way. Let's say you've hooked up digital I/O P1.0
to analog input AI0, and your analog out AI1 to analog input AI1::

    >>> from instrumental.drivers.daq.ni import NIDAQ, list_instruments
    >>> list_instruments()
    [<NIDAQ 'Dev0'>]
    >>> daq = NIDAQ('Dev0')
    >>> daq.ai0.read()
    <Quantity(0.0154385786803, 'volt)>
    >>> daq.port1[0].write(True)
    >>> daq.ai0.read()
    <Quantity(5.04241962841, 'volt')>
    >>> daq.ao1.write('2.1V')
    >>> daq.ai1.read()
    <Quantity(2.10033320744, 'volt')>

Now let's try using digital input. Assume P1.1 is attached to P1.2::

    >>> daq.port1[1].write(False)
    >>> daq.port1[2].read()
    False
    >>> daq.port[1].write(True)
    >>> daq.port1[2].read()
    True

Let's read and write more than one bit at a time. To write to multiple lines
simultaneously, pass an unsigned int to `write()`. The line with the lowest
index corresponds to the lowest bit, and so on. If you read from multiple
lines, read() returns an int. Connect P1.0-3 to P1.4-7::

   >>> daq.port1[0:3].write(5)
   >>> daq.port1[4:7].read()  # Note that the last index IS included
   5
   >>> daq.port1[7:4].read()  # This flips the ordering of the bits
   10
   >>> daq.port1[0].write(False)  # Zero the ones bit individually
   >>> daq.port1[4:7].read()
   4

You can also read and write arrays of buffered data. Use the same `read()` and
`write()` methods, just include your timing info (and pass in the data as an
array if writing). You must provide two of `duration`, `freq`, and `n_samples`
to uniquely determine the timing info. For example, there are three ways to
output the same sinusoid::

    >>> from instrumental import u
    >>> from numpy import pi, sin, linspace
    >>> data = sin( 2*pi * linspace(0, 1, 101) )*5*u.V + 5*u.V
    >>> daq.ao0.write(data, duration='1s', freq='100Hz')
    >>> daq.ao0.write(data, duration='1s', n_samps=101)
    >>> daq.ao0.write(data, freq='100Hz', n_samps=101)

Note that the endpoint of the duration is included, e.g. 1 second of data output at
a sample rate of 100 Hz corresponds to 101 samples.

All this stuff is great for simple tasks, but sometimes you may want to perform
input and output on multiple channels simultaneously. To accomplish this we need
to use Tasks.

.. NOTE::
    Tasks in the `ni` module are similar, but not the same as Tasks in DAQmx
    (and PyDAQmx). Our Tasks allow you to quickly and easily perform simultaneous
    input and output with one Task without the hassle of having to create multiple
    and hook their timing and triggers up.

Here's an example of how to perform simultaneous input and output::

    >>> from instrumental.drivers.daq.ni import NIDAQ, Task
    >>> from instrumental import u
    >>> from numpy import linspace
    >>> daq = NIDAQ('Dev0')
    >>> task = Task(daq.ao0, daq.ai0)
    >>> task.set_timing(duration='1s', freq='10Hz')
    >>> write_data = {'ao0': linspace(0, 10, 11) * u.V}
    >>> read_data = task.run(write_data)
    {u'ai0': <Quantity([  1.00000094e+01   1.89578724e-04   9.99485542e-01   2.00007917e+00
       3.00034866e+00   3.99964556e+00   4.99991698e+00   5.99954114e+00
       6.99981625e+00   7.99976941e+00   9.00037441e+00], 'volt')>,
     u't': <Quantity([ 0.   0.1  0.2  0.3  0.4  0.5  0.6  0.7  0.8  0.9  1. ], 'second')>}

As you can see, we create a dict as input to the `run()` method. Its keys are the names
of the input channels, and its values are the corresponding array Quantities that we want to write.
Similarly, the `run()` returns a dict that contains the input that was read. This dict also contains 
the time data under key 't'.


Module Reference
----------------

.. automodule:: instrumental.drivers.daq.ni
    :members:
    :undoc-members:
