NiceLib Driver Example
======================

.. contents::
    :local:
    :depth: 2

---------------------------------------------------------------------------------

In this guide, we'll run through the process of writing a driver that uses NiceLib to wrap a C library, using the example of an NI DAQ. A NiceLib-based driver consists of three parts: low-level, mid-level, and high-level interfaces.

Low-level
    Mimics the C interface directly

Mid-level
    Has the same functions as the low-level interface, but with a more convenient interface

High-level
    Is nice and pythonic, often doesn't necessarily mimic the C interface's structure


Low-Level Interface
-------------------

The Build File
~~~~~~~~~~~~~~
NiceLib semi-automatically generates a low-level interface for us. To tell it how to do so, we create a build file, which contains a ``build()``. This function invokes ``build_lib()`` with arguments that tell it what library (.dll/.so file) we're wrapping and what header(s) to use.

For our ``ni`` library, we name our file ``_build_ni.py``::

    # _build_ni.py
    from nicelib import build_lib

    header_info = r'C:\Program Files (x86)\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h'
    lib_name = 'nicaiu'


    def build():
        build_lib(header_info, lib_name, '_nilib', __file__)


    if __name__ == '__main__':
        from instrumental.log import log_to_screen
        log_to_screen(fmt='%(message)s')
        build()

You can see we've indicated the path to the header ``NIDAQmx.h`` and the library ``nicaiu.dll`` that are used by the Windows version of NI-DAQmx.

Now let's manually invoke a build:

.. code-block:: shell

    $ python _build_ni.py
    Module _nilib does not yet exist, building it now. This may take a minute...
    Searching for headers...
    Found C:\Program Files (x86)\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h
    Parsing and cleaning headers...
    Successfully parsed input headers
    Compiling cffi module...
    Writing macros...
    Done building _nilib


Nice, it worked! We now have a freshly-generated ``_nilib.py`` module, which is our low-level interface. You can then call ``load_lib('foo', __package__)`` to load the ``LibInfo`` object, as we'll see in the mid-level interface section.

Parsing Problems?
~~~~~~~~~~~~~~~~~
We won't always be this fortunate, since headers sometimes include nonstandard syntax which nicelib's parsing system can't handle. In that case, there are two basic approaches:

1. Manually include only the necessary snippets of the header, cleaning up any unparseable syntax.
2. Use ``build_lib``\'s options, including ``token_hooks`` and ``ast_hooks`` to avoid or programmatically clean up the problem syntax.

Option 1 can be good for quickly moving on and starting to write your mid-level interface. You can include just a few functions that you want to test out, and perhaps later come back and pursue option 2. For example, we could do the following for our DAQmx driver::

    from nicelib import build_lib

    source = """
    #define __CFUNC         __stdcall
    typedef signed int int32;
    typedef unsigned int uInt32;

    int32 __CFUNC DAQmxGetSysDevNames(char *data, uInt32 bufferSize);
    int32 __CFUNC DAQmxGetDevProductNum(const char device[], uInt32 *data);
    int32 __CFUNC DAQmxGetDevSerialNum(const char device[], uInt32 *data);
    """
    lib_name = 'nicaiu'


    def build():
        build_lib(None, lib_name, '_nilib', __file__, preamble=source)

We use ``header_info=None`` to skip loading any external header files, and pass in our source via the ``preamble`` parameter.


Option 2 is more complete, but can sometimes be tricky, as it requires some extra knowledge of C and why some section of code may not be parsing correctly (e.g. because it's *actually* C++, which happens commonly in some libs written only for Windows). In the simplest case, you may just need to exclude a problematic header that's being included, or use one of the pre-written token hooks or ast hooks that nicelib provides. In other cases, you may need to write your own hook to clean up the header. See the `nicelib docs <http://nicelib.readthedocs.io/en/stable/building.html#processing-headers>`_ for a more detailed account of how to use token/ast hooks and the other paramters of ``build_lib()``.


Mid-Level Interface
-------------------

Once we have a low-level interface that can be loaded via ``load_lib()``, we can start to work on the mid-level bindings. What's the point of these bindings? Well, they make the functions a lot more hospitable to work with. Take for example ``int32 DAQmxGetSysDevNames(char *data, uInt32 bufferSize)``. This function takes a preallocated ``char`` buffer and its length, returning its string within the buffer, and an error code as the ``int32`` return value. Using the low-level binding looks like this::

    buflen = 1024
    data = ffi.new('char[]', buflen)
    retval = DAQmxGetSysDevNames(data, buflen)
    handle_daq_retval(retval)
    result = ffi.string(data)

Seems kinda verbose---and this function only takes two arguments! Write too much code like this and your code's intent will drown in a sea of bookkeeping. In contrast, using a mid-level binding looks like this::

     result = NiceNI.GetSysDevNames()

Better, right? So how do you write these mid-level bindings? Here's a simple start::

    from nicelib import load_lib, NiceLib, Sig

    class NiceNI(NiceLib):
        _info_ = load_lib('ni', __package__)
        _prefix_ = 'DAQmx'

        GetErrorString = Sig('in', 'buf', 'len')
        GetSysDevNames = Sig('buf', 'len')
        CreateTask = Sig('in', 'out')

We define a subclass of ``NiceLib`` that specifies some general info about the library, as well as some signature (``Sig``) definitions for the functions we want to wrap. ``_info_`` specifies the lib we're wrapping, and ``_prefix_`` is a prefix that will be removed from the names of the functions. A ``Sig`` specifies the purpose of each of its function's parameters, e.g. whether it's an input, an output, or something more special.

For instance, ``CreateTask`` was  was matched with ``Sig('in', 'out')``, reflecting that ``int32 DAQmxCreateTask(const char taskName[], TaskHandle *taskHandle)`` uses ``taskName`` as an input, and ``taskHandle`` as an output. This tells nicelib that ``CreateTask`` takes only one argument and returns one value, and nicelib creates a function accordingly:

.. code-block:: ipython

    In [1]: NiceNI.CreateTask('myTask')
    Out[1]: (<cdata 'void *' 0x000000000AD49250>, 0)

But wait, there are two values here, what's going on? The first part makes sense, that's our ``taskHandle`` (of type ``TaskHandle``, an alias for ``void*``), but what's the zero from? It's the *actual* return value, the error-code of type ``int32``. What if we want to ignore this value, or do something else with it? That's where ``RetHandler``\s come in. We'll talk more about these later, but nicelib comes with two builtin return handlers, ``ret_return`` and ``ret_ignore``. ``ret_return`` is used by default, and it tacks the C return value on the the end of the Python return values. ``ret_ignore`` simply ignores the return value. There are a few levels at which we can specify the return handler, but to apply it to all functions within the lib we use the ``_ret_`` attribute:

.. code-block:: python

   from nicelib import load_lib, NiceLib, Sig, ret_ignore

   class NiceNI(NiceLib):
       _info_ = load_lib('ni', __package__)
       _prefix_ = 'DAQmx'
       _ret_ = ret_ignore

       GetErrorString = Sig('in', 'buf', 'len')
       GetSysDevNames = Sig('buf', 'len')
       CreateTask = Sig('in', 'out')

Now let's try again:

.. code-block:: ipython

   In [1]: NiceNI.CreateTask('myTask')
   Out[1]: <cdata 'void *' 0x0000000009169250>

For now let's ignore the return codes; we'll handle them properly later. Now that we've explained ``'in'`` and ``'out'``, what do ``'buf'`` and ``'len'`` do? Recall that ``DAQmxGetSysDevNames(char *data, uInt32 bufferSize)`` takes a ``char`` buffer and its length, writing a C-string into the buffer. The pair of ``'buf'`` and ``'len'`` are made for exactly such a situation---nicelib will create a ``char`` array, passing it in for the ``'buf'`` parameter, and its length in as the ``'len'`` parameter, then extracting a ``bytes`` object using ``ffi.string()`` and returning it:

.. code-block:: ipython

   In [2]: NiceNI.GetSysDevNames()
   Out[2]: b'Dev1'

You can check out the nicelib docs to find a listing of all the possible ``Sig`` string codes and what they do.


TODO:

- NiceObject classdefs
- RetHandlers


High-Level Interface
--------------------

Now let's get start writing our driver::

   from instrumental.drivers.daq import DAQ

   class NIDAQ(DAQ):
       _INST_PARAMS_ = ['name', 'serial', 'model']

       def _initialize(self):
           self.name = self._paramset['name']
           self._dev = self.mx.Device(self.name)

We inherit from ``DAQ``, a subclass of ``Instrument``, and use the ``_INST_PARAMS_`` class attribute to declare what parameters our instrument can use to construct itself.

