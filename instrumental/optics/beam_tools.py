# -*- coding: utf-8 -*-
# Copyright 2013-2016 Nate Bogdanowicz

import numpy as np
from functools import reduce
from numpy import sqrt, complex, sign, linspace, pi
from scipy.special import erfinv
from optical_elements import Space
from .. import Q_


def _get_real(q):
    """Temporary hack to add units to `real`"""
    return Q_(q.magnitude.real, q.units)


def _get_imag(q):
    """Temporary hack to add units to `real`"""
    return Q_(q.magnitude.imag, q.units)


def _find_cavity_mode(M):
    """
    Returns 1/q for a cavity eigenmode given the effective cavity matrix M.
    """
    A, B, C, D = M.elems()

    # From Siegman: Lasers, Chapter 21.1
    term1 = (D-A)/(2*B)
    term2 = 1/B*sqrt(complex(((A+D)/2)**2 - 1))
    sgn = sign(_get_imag(term2))

    # Choose transversely confined solution
    q_r = term1 - sgn*term2

    # Check stability to perturbation
    if ((A+D)/2)**2 > 1:
        raise Exception('Resonator is unstable')
    return q_r


def find_cavity_modes(elems):
    """
    Find the eigenmodes of an optical cavity.

    Parameters
    ----------
    elems : list of OpticalElements
        ordered list of the cavity elements

    Returns
    -------
    qt_r, qs_r : complex Quantity objects
        1/q for the tangential and sagittal modes, respectively. Has
        units of 1/[length].
    """
    qt_r = _find_cavity_mode(reduce(lambda x, y: y*x, [el.tan for el in elems]))
    qs_r = _find_cavity_mode(reduce(lambda x, y: y*x, [el.sag for el in elems]))
    return qt_r, qs_r


def get_zR(q_r):
    """ Get Rayleigh range zR from reciprocal beam parameter q_r """
    q_r = Q_(q_r).to('1/mm')
    return _get_imag(1/q_r)


def get_w0(q_r, lambda_med):
    """
    Get waist size w0 of light with in-medium wavelength lambda_med
    and reciprocal beam parameter q_r
    """
    q_r = Q_(q_r).to('1/mm')
    lambda_med = Q_(lambda_med).to('nm')
    return sqrt(lambda_med*get_zR(q_r)/pi)


def get_z0(q_r):
    """ Get z-location z0 of the focus from reciprocal beam parameter q_r """
    q_r = Q_(q_r).to('1/mm')
    return _get_real(1/q_r)


def beam_profile(q_r, z_meas, z, lambda_med, clipping=None):
    q_r = Q_(q_r).to('1/mm')
    z_meas = Q_(z_meas).to('mm')
    z = Q_(z).to('mm')
    lambda_med = Q_(lambda_med).to('nm')

    w0 = get_w0(q_r, lambda_med)
    zR = get_zR(q_r)
    z0 = get_z0(q_r)
    scale = 1
    if clipping is not None:
        scale = -erfinv(2*clipping - 1)/sqrt(2)
    return scale*w0*sqrt(1 + ((z+z0-z_meas)/zR)**2)


def beam_roc(q_r, z_meas, z, n):
    q_r = Q_(q_r).to('1/mm')
    z_meas = Q_(z_meas).to('mm')
    z = Q_(z).to('mm')

    zR = get_zR(q_r)
    z0 = get_z0(q_r)

    # R is commonly infinite, so we must ignore divide by zero warnings here
    old_settings = np.seterr(divide='ignore')

    R = _get_real(1/(z0+z-z_meas + 1j*zR))

    # Restore divide-by-zero warnings
    np.seterr(**old_settings)

    return R


def _unitful_linspace(start, stop, *args, **kwds):
    start, stop = Q_(start), Q_(stop)
    units = start.units
    raw_pts = linspace(start.m, stop.m_as(units), *args, **kwds)
    return Q_(raw_pts, units)


def get_profiles(q_r, lambda0, orientation, elements, clipping=None, zeroat=0):
    q_r = Q_(q_r).to('1/mm')
    lambda0 = Q_(lambda0).to('nm')

    zs, profiles, RoCs = [], [], []
    cur_z = Q_(0, 'mm')
    z0 = Q_(0, 'mm')

    rev_elems = list((elements))
    for i, el in enumerate(rev_elems):
        if i == zeroat % len(rev_elems):
            z0 = cur_z

        # Get beam profile inside 'Space' elements
        if isinstance(el, Space):
            z = _unitful_linspace(cur_z, cur_z + el.d, 10000, endpoint=(i == len(rev_elems)-1))
            zs.append(z)
            profiles.append(beam_profile(q_r, cur_z, z, lambda0/el.n, clipping))
            RoCs.append(beam_roc(q_r, cur_z, z, el.n))
            cur_z += el.d

        # Propagate q_r through the current element
        M = el.sag if orientation == 'sagittal' else el.tan
        A, B, C, D = M.elems()
        q_r = (C + D*q_r)/(A + B*q_r)

    for i, z in enumerate(zs):
        zs[i] = z-z0

    return zs, profiles, RoCs
