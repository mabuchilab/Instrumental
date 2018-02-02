FAQs
====

My instrument isn't showing up in ``list_instruments()``. What now?
-------------------------------------------------------------------

If you're using this particular driver for the first time, make sure you've followed the install directions fully. You should also check that the device works with any vendor-provided software (e.g. a camera viewer GUI). If the device still isn't showing up, you should import the driver module directly to reveal any errors (see :ref:`list_instruments-no-error`).


.. _list_instruments-no-error:

Why isn't ``list_instruments()`` producing any errors?
------------------------------------------------------

``list_instruments()`` is designed to check all Instrumental drivers that are available, importing each driver in turn. If a driver fails to import, this is often because you haven't installed its requirements (because you're not using it), so ``list_instruments()`` simply ignores the error and moves on.



