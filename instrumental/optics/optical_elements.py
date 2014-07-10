# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from numbers import Number
from numpy import cos, sin, arcsin
from .. import Q_


def _parse_angle(ang):
    """
    If ang is a number, treats it as in degrees. Otherwise it does the usual
    unit parsings from Q_
    """
    if isinstance(ang, Number):
        ang = Q_(ang, 'deg')
    else:
        ang = Q_(ang)
    return ang


class ABCD(object):
    """A simple ABCD (ray transfer) matrix class.

    ABCD objects support mutiplication with scalar numbers and other ABCD
    objects.
    """
    def __init__(self, A, B, C, D):
        """Create an ABCD matrix from its elements.

        The matrix is a 2x2 of the form::

            [A B]
            [C D]

        Parameters
        ----------
        A,B,C,D : Quantity objects
            `A` and `D` are dimensionless. `B` has units of [length] (e.g. 'mm'
            or 'rad/mm'), and `C` has units of 1/[length].
        """
        self.A = Q_(A).to('dimensionless')
        self.B = Q_(B).to('mm/rad')
        self.C = Q_(C).to('rad/mm')
        self.D = Q_(D).to('dimensionless')

    def __mul__(self, other):
        if isinstance(other, ABCD):
            A = self.A*other.A + self.B*other.C
            B = self.A*other.B + self.B*other.D
            C = self.C*other.A + self.D*other.C
            D = self.C*other.B + self.D*other.D
            return ABCD(A, B, C, D)
        elif isinstance(other, (int, float)):
            return ABCD(A*other, B*other, C*other, D*other)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, ABCD):
            A = other.A*self.A + other.B*self.C
            B = other.A*self.B + other.B*self.D
            C = other.C*self.A + other.D*self.C
            D = other.C*self.B + other.D*self.D
            return ABCD(A, B, C, D)
        elif isinstance(other, (int, float)):
            return ABCD(self.A*other, self.B*other, self.C*other, self.D*other)
        return NotImplemented

    def _stringify(self, q):
        s = str(q)
        s = s.replace('dimensionless', '')
        s = s.replace('millimeter', 'mm')
        s = s.replace('radian', 'rad')
        s = s.replace(' / ', '/')
        return s.strip()

    def __repr__(self):
        strA = self._stringify(self.A)
        strB = self._stringify(self.B)
        strC = self._stringify(self.C)
        strD = self._stringify(self.D)

        diff = len(strA) - len(strC)
        if diff > 0:
            strC = " "*(diff-diff//2) + strC + " "*(diff//2)
        else:
            diff = -diff
            strA = " "*(diff-diff//2) + strA + " "*(diff//2)

        diff = len(strB) - len(strD)
        if diff > 0:
            strD = " "*(diff-diff//2) + strD + " "*(diff//2)
        else:
            diff = -diff
            strB = " "*(diff-diff//2) + strB + " "*(diff//2)

        return "[{} , {}]\n[{} , {}]".format(strA, strB, strC, strD)

    def elems(self):
        """Get the matrix elements.

        Returns
        -------
        A, B, C, D : tuple of Quantity objects
            The matrix elements
        """
        return self.A, self.B, self.C, self.D


class OpticalElement(object):
    def __init__(self, tan, sag):
        self.tan = tan
        self.sag = sag

    def __mul__(self, other):
        tan = self.tan * other.tan
        sag = self.sag * other.sag
        return OpticalElement(tan, sag)

    def __rmul__(self, other):
        tan = other.tan * self.tan
        sag = other.sag * self.sag
        return OpticalElement(tan, sag)


class Space(OpticalElement):
    """A space between other optical elements"""
    def __init__(self, d, n=1):
        """
        Parameters
        ----------
        d : Quantity or str
            The axial length of the space
        n : number, optional
            The index of refraction of the medium. Defaults to 1 for vacuum.
        """
        d = Q_(d).to('mm/rad')

        self.tan = ABCD(1,          d,
                        '0 rad/mm', 1)
        self.sag = self.tan
        self.d = d
        self.n = n


class Lens(OpticalElement):
    """A thin lens"""
    def __init__(self, f):
        """
        Parameters
        ----------
        f : Quantity or str
            The focal length of the lens
        """
        f = Q_(f).to('mm/rad')

        self.tan = ABCD( 1,   '0 mm/rad',
                        -1/f,     1     )
        self.sag = self.tan


class Mirror(OpticalElement):
    """A mirror, possibly curved"""
    def __init__(self, R=None, aoi=0):
        """
        Parameters
        ----------
        R : Quantity or str, optional
            The radius of curvature of the mirror's spherical surface. Defaults
            to `None`, indicating a flat mirror.
        aoi : Quantity or str or number, optional
            The angle of incidence of the beam on the mirror, defined as the
            angle between the mirror's surface normal and the beam's axis.
            Defaults to 0, indicating normal incidence.
        """
        R = Q_(R).to('mm') if R else Q_(float('inf'), 'mm')
        aoi = _parse_angle(aoi)

        self.tan = ABCD(1,              '0 mm/rad',
                        -2/(R*cos(aoi)),     1    )
        self.sag = ABCD(1,              '0 mm/rad',
                        -2*cos(aoi)/R,       1    )


class Interface(OpticalElement):
    """An interface between media with different refractive indices"""
    def __init__(self, n1, n2, R=None, aoi=None, aot=None):
        """
        Parameters
        ----------
        n1 : number
            The refractive index of the initial material
        n2 : number
            The refractive index of the final material
        R : Quantity or str, optional
            The radius of curvature of the interface's spherical surface, in
            units of length. Defaults to `None`, indicating a flat interface.
        aoi : Quantity or str or number, optional
            The angle of incidence of the beam relative to the interface,
            defined as the angle between the interface's surface normal and the
            _incident_ beam's axis.  If not specified but `aot` is given, aot
            will be used. Otherwise, `aoi` is assumed to be 0, indicating
            normal incidence. A raw number is assumed to be in units of
            degrees.
        aot : Quantity or str or number, optional
            The angle of transmission of the beam relative to the interface,
            defined as the angle between the interface's surface normal and
            the *transmitted* beam's axis. See `aoi` for more details.
        """
        R = Q_(R).to('mm') if R else Q_(float('inf'), 'mm')

        if aoi is None:
            if aot is None:
                theta1 = Q_(0)
                theta2 = Q_(0)
            else:
                theta2 = _parse_angle(aot)
                theta1 = arcsin(n2/n1*sin(theta2))
        else:
            if aot is None:
                theta1 = _parse_angle(aoi)
                theta2 = arcsin(n1/n2*sin(theta1))
            else:
                raise Exception("Cannot specify both aoi and aot")

        d_ne_t = 1/cos(theta1) - n1/(n2*cos(theta2))
        d_ne_s = cos(theta2) - n1/n2*cos(theta1)
        self.tan = ABCD(cos(theta2)/cos(theta1),            '0 mm/rad',
                        d_ne_t/R,                n1/n2*cos(theta1)/cos(theta2))
        self.sag = ABCD(   1,     '0 mm/rad',
                        d_ne_s/R,   n1/n2   )
