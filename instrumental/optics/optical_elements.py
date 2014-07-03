# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from numpy import array, deg2rad, cos, sin, arcsin

class Space(object):
    """A space between other optical elements"""
    def __init__(self, d, n=1):
        """
        Parameters
        ----------
        d : number
            The axial length of the space
        n : number, optional
            The index of refraction of the medium. Defaults to 1 for vacuum.
        """
        self.tan = array( [[1, d], [0, 1]] )
        self.sag = self.tan
        self.d = d
        self.n = n

class Lens(object):
    """A thin lens"""
    def __init__(self, f):
        """
        Parameters
        ----------
        f : number
            The focal length of the lens
        """
        self.tan = array( [[1, 0], [-1/f, 1]] )
        self.sag = self.tan

class Mirror(object):
    """A mirror, possibly curved"""
    def __init__(self, R=float('inf'), aoi=0):
        """
        Parameters
        ----------
        R : number, optional
            The radius of curvature of the mirror's spherical surface. Defaults
            to infinity, indicating a flat mirror.
        aoi : number, optional
            The angle of incidence of the beam on the mirror, defined as the
            angle between the mirror's surface normal and the beam's axis.
            Defaults to 0, indicating normal incidence.
        """
        rad = deg2rad(aoi)
        self.tan = array( [[1, 0], [-2/(R*cos(rad)), 1]] )
        self.sag = array( [[1, 0], [-2*cos(rad)/R, 1]] )

class Interface(object):
    """An interface between media with different refractive indices"""
    def __init__(self, n1, n2, R=float('inf'), aoi=None, aot=None):
        """
        Parameters
        ----------
        n1 : number
            The refractive index of the initial material
        n2 : number
            The refractive index of the final material
        R : number, optional
            The radius of curvature of the interface's spherical surface.
            Defaults to infinity, indicating a flat interface.
        aoi : number, optional
            The angle of incidence of the beam relative to the interface,
            defined as the angle between the interface's surface normal and the
            _incident_ beam's axis.  If not specified but aot is given, aot
            will be used. Otherwise, aoi is assumed to be 0, indicating normal
            incidence.
        aot : number, optional
            The angle of transmission of the beam relative to the interface,
            defined as the angle between the interface's surface normal and
            the _transmitted_ beam's axis. See aoi for more details.
        """
        if aoi is None:
            if aot is None:
                theta1 = 0
                theta2 = 0
            else:
                theta2 = deg2rad(aot)
                theta1 = arcsin(n2/n1*sin(theta2))
        else:
            if aot is None:
                theta1 = deg2rad(aoi)
                theta2 = arcsin(n1/n2*sin(theta1))
            else:
                raise Exception("Cannot specify both aoi and aot")

        d_ne_t = 1/cos(theta1) - n1/(n2*cos(theta2))
        d_ne_s = cos(theta2) - n1/n2*cos(theta1)
        self.tan = array( [[cos(theta2)/cos(theta1), 0], [d_ne_t/R, n1/n2*cos(theta1)/cos(theta2)]] )
        self.sag = array( [[1, 0], [d_ne_s/R, n1/n2]] )
