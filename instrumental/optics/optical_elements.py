# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

from numpy import array, deg2rad, cos, sin, arcsin

class Space(object):
    def __init__(self, d, n=1):
        self.tan = array( [[1, d], [0, 1]] )
        self.sag = self.tan
        self.d = d
        self.n = n

class Lens(object):
    def __init__(self, f):
        self.tan = array( [[1, 0], [-1/f, 1]] )
        self.sag = self.tan

class Mirror(object):
    def __init__(self, R=float('inf'), aoi=0):
        rad = deg2rad(aoi)
        self.tan = array( [[1, 0], [-2/(R*cos(rad)), 1]] )
        self.sag = array( [[1, 0], [-2*cos(rad)/R, 1]] )

class Interface(object):
    def __init__(self, n1, n2, R=float('inf'), aoi=None, aot=None):
        # Allow user to enter either angle of incidence or transmission
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
