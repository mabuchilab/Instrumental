Change Log
==========

Unreleased
----------

Added
"""""
- Package metadata now (mostly) consolidated in ``__about__.py``


(0.2.1) - 2016-01-13
--------------------

Added
"""""
- Support for building cffi modules via setuptools
- Packaging support

Changed
"""""""
- instrumental.conf is now installed upon first-use. This allows us to eliminate the post_install
  script. Hopefully there will be future support (via wheels) to do this upon install instead
- slightly better error message for failure when importing a specified module in ``instrument()``

Removed
"""""""
- Outdated example scripts


(0.2) - 2015-12-15
------------------

Added
"""""
- Everything, technically, but recent changes include:
- ``NiceLib``, a class to aid wrapping typical DLLs
- Unit-checking decorators
- ``RemoteInstrument`` for using instruments controlled by a separate computer

Changed
"""""""
- Camera class is now an abstract base class with abstract methods and properties

Removed
"""""""
- ``FakeVISA`` (in favor of ``RemoteInstrument``)
