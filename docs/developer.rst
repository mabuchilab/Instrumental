Developer's Guide
=================

This page is for those of you who enjoy diving into guidelines, coding conventions, and project philosophies. If you're looking to get started more quickly, instead check out the :doc:`contributing` and :doc:`driver-dev` pages.

-------------------------------------------------------------------------------

.. contents::
    :local:
    :depth: 1

-------------------------------------------------------------------------------

.. toctree::
   :maxdepth: 2

   driver-table
   release-instructions

-------------------------------------------------------------------------------

The Instrumental Manifesto
--------------------------

A major goal of Instrumental is to try to unify and simplify a lot of common,
useful operations. Essential to that is a consistent and coherent interface.

* Simple, common tasks should be simple to perform
* Options should be provided to enable more complex tasks
* Documentation is essential
* Use of physical units should be standard and widespread


Simple, common tasks should be simple to perform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tasks that are conceptually simple or commonly performed should be made easy.
This means having sane defaults.

Options should be provided to enable more complex tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Along with sane defaults, provide *options*. Typically, this means providing optional parameters in functions and methods.

Documentation is essential
~~~~~~~~~~~~~~~~~~~~~~~~~~
Providing Documentation can be tiring or boring, but, without it, your carefully crafted interfaces can be opaque to others (including future-you). In particular, all functions and methods should have brief summary sentences, detailed explanations, and descriptions of their parameters and return values.

This also includes providing useful error messages and warnings that the
average user can actually understand and do something with.

Use of physical units should be standard and widespread
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Units in scientific code can be a big issue. Instrumental incorporates
unitful quantities using the very nice `Pint`_ package. While units are great,
it can seem like extra work to start using them. Instrumental strives to use
units everywhere to encourage their widespread use.

.. _Pint: http://pint.readthedocs.org

-------------------------------------------------------------------------------

Coding Conventions
------------------

As with most Python projects, you should be keeping in mind the style
suggestions in `PEP8`_. In particular:

* Use 4 spaces per indent (not tabs!)
* Classes should be named using ``CapWords`` capitalization
* Functions and methods should be named using ``lower_case_with_underscores``

  * As an exception, python wrapper (e.g. cffi/ctypes) code used as a _thin_ wrapper
    to an underlying library may stick with its naming convention for
    functions/methods. (See the docs for Attocube stages for an example of this)

* Modules and packages should have short, all-lowercase names, e.g.
  ``drivers``
* Use a ``_leading_underscore`` for non-public functions, methods, variables,
  etc.
* Module-level constants are written in ``ALL_CAPS``

Strongly consider using a plugin for your text editor (e.g. `vim-flake8`_) to
check your PEP8 compliance.

It is OK to have lines over 80 characters, though they should almost always be 100 characters or
less.

.. _PEP8: http://legacy.python.org/dev/peps/pep-0008
.. _vim-flake8: https://github.com/nvie/vim-flake8


-------------------------------------------------------------------------------


Docstrings
----------

Code in Instrumental is primarily documented using python docstrings, following the `numpydoc conventions`_. In general, you should also follow the guidelines of `pep 257`_.

- No spaces after the opening triple-quote
- One-line docstrings should be on a single line, e.g. ``"""Does good stuff."""``
- Multi-liners have a summary line, followed by a blank line, followed by the rest of the doc. The
  closing quote should be on its own line

.. _pep 257: https://www.python.org/dev/peps/pep-0257/
.. _numpydoc conventions: https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt#docstring-standard


-------------------------------------------------------------------------------


Python 2/3 Compatibility
------------------------

Instrumental was originally developed for Python 2.7 and long maintained Python 2/3 cross compatibility. As of release 0.7, we haved dropped that support and now require Python 3.7+. This means all future development should target Python 3.

Python 2 support may be removed from existing code as a part of future development, though this is not currently a priority.

-------------------------------------------------------------------------------


Developing Drivers
------------------

If you're considering writing a driver, thank you! Check out :doc:`driver-dev` for details.
