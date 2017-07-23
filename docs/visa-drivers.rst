Writing VISA-based Drivers
--------------------------
To control instruments using message-based protocols, you should use `PyVISA`_.

If you need to open/access the VISA instrument/resource (e.g. within ``_instrument()``), you should use ``_get_visa_instrument()`` to take advantage of caching

.. _PyVISA: https://pyvisa.readthedocs.io/
