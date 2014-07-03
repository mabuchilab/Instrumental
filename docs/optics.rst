Optics
======

Instrumental's Optics package is useful for exploring and scripting basic gaussian optics using the ABCD matrix approach. The package is split up into three main categories: optical elements, beam tools, and beam plotting tools.


Optical Elements
----------------

Instrumental's optical elements are based on simple numerical ABCD matrix representations and include Mirrors, Lenses, Spaces, and Interfaces. Each provides a useful constructor to create them in a way that's conceptually simple and clear.

.. autoclass:: instrumental.optics.optical_elements.Mirror
    :members:

.. autoclass:: instrumental.optics.optical_elements.Lens
    :members:

.. autoclass:: instrumental.optics.optical_elements.Interface
    :members:

.. autoclass:: instrumental.optics.optical_elements.Space
    :members:
