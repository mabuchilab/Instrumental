# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz
"""
Module containing utilities related to fitting.

Still very much a work in progress...
"""

from numpy import (square, extract, diff, sign, logical_and,
                   searchsorted, log, sum, exp, ma, pi)
import scipy.optimize
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor

# MatplotlibDeprecationWarning moved to cbook in version 1.3.0
# and was added in version 1.2.1rc1
try:
    from matplotlib.cbook import MatplotlibDeprecationWarning
except ImportError:
    try:
        from matplotlib import MatplotlibDeprecationWarning
    except ImportError:
        MatplotlibDeprecationWarning = None

import warnings

from . import u, Q_


def _ginput(*args, **kwargs):
    """
    Hides the stupid default warnings when using ginput. There has to be
    a better way...
    """
    if MatplotlibDeprecationWarning is None:
        return plt.ginput(*args, **kwargs)
    else:
        warnings.simplefilter('ignore', MatplotlibDeprecationWarning)
        out = plt.ginput(*args, **kwargs)
        warnings.warn('default', MatplotlibDeprecationWarning)
        return out


def curve_fit(f, xdata, ydata, p0=None, sigma=None, **kw):
    """
    Wrapper for scipy's curve_fit that works with pint Quantities.
    """
    # - needs to check unit "correctness"
    # f() must be written properly such that it works with 'raw' numbers if
    # they're in base units

    # Only use pint if at least one of the inputs is a pint Quantity
    use_pint = False
    nums = [xdata, ydata]
    nums.extend(p0)
    for num in nums:
        if isinstance(num, Q_):
            use_pint = True
            break

    if not use_pint:
        return scipy.optimize.curve_fit(f, xdata, ydata, p0, sigma, **kw)

    xdata_mag = xdata.to_base_units().magnitude
    ydata_mag = ydata.to_base_units().magnitude
    if p0:
        p0_mag = [p.to_base_units().magnitude for p in p0]
    else:
        p0_mag = None

    popt_mag, pcov_mag = scipy.optimize.curve_fit(f, xdata_mag, ydata_mag,
                                                  p0_mag, **kw)
    popt = []
    pcov = []
    if p0:
        for _p0, _popt_mag, pcov_mag_row in zip(p0, popt_mag, pcov_mag):
            # Convert from base_unit magnitude back to the original units
            popt.append( Q_(_popt_mag, _p0.to_base_units().units).to(_p0.units) )
            pcov_row = []
            for _p0_2, _pcov_mag in zip(p0, pcov_mag_row):
                pcov_row.append( Q_(_pcov_mag, (_p0*_p0_2).to_base_units().units).to(_p0*_p0_2) )
            pcov.append(pcov_row)
    else:
        popt = popt_mag
        pcov = pcov_mag

    return popt, pcov


def lorentzian(x, A, x0, FWHM):
    """
    Lorentzian curve. Takes an array ``x`` and returns an array
    :math:`\\frac{A}{1 + (\\frac{2(x-x0)}{FWHM})^2}`
    """
    return A / (1 + square( 2*(x-x0)/FWHM ))


def triple_lorentzian(nu, A0, B0, FWHM, nu0, dnu, y0):
    """
    Triple lorentzian curve. Takes an array ``nu`` and returns an array
    that is the sum of three lorentzians
    ``lorentzian(nu, A0, nu0, FWHM) + lorentzian(nu, B0, nu0-dnu, FWHM)
    + lorentzian(nu, B0, nu0+dnu, FWHM)``.
    """
    t1 = lorentzian(nu, A0, nu0, FWHM)
    t2 = lorentzian(nu, B0, nu0-dnu, FWHM)
    t3 = lorentzian(nu, B0, nu0+dnu, FWHM)
    return t1 + t2 + t3 + y0


def _estimate_FWHM_pint(nu, amp, half_max, left_limit, center, right_limit):
    """ Pint-friendly way to estimate FWHM. Doesn't use 'bad' numpy stuff"""
    left_sum, right_sum = 0 * u.MHz, 0 * u.MHz
    divisor = 0
    i = 0
    while nu[i] < left_limit:
        i += 1
    while nu[i] < center:
        if amp[i-1] <= half_max and amp[i] > half_max:
            left_sum += nu[i]
            divisor += 1
        i += 1
    left_mean = left_sum / divisor
    divisor = 0

    while nu[i] < right_limit:
        if amp[i-1] >= half_max and amp[i] < half_max:
            right_sum += nu[i]
            divisor += 1
        i += 1
    right_mean = right_sum / divisor
    return right_mean - left_mean


def _estimate_FWHM(nu, amp, half_max, left_limit, center, right_limit):
    # Get x values of points where the data crosses half_max
    all_points = extract(diff(sign(amp-half_max)), nu)

    # Filter out the crossings from the sidebands
    middle_points = extract(logical_and(left_limit < all_points, all_points < right_limit),
                            all_points)
    center_index = searchsorted(middle_points, center)
    FWHM = middle_points[center_index:].mean() - middle_points[:center_index].mean()
    return FWHM


def _linear_fit_decay(x, y):
    # Takes ndarrays for now, DON'T USE PINT QUANTITIES!
    # From wolfram Mathworld; Need to fix to re-use some calculations!!

    # Linearize by removing offset
    c = y[-20:].mean()
    y = y - c

    # Mask out negative values that log() can't handle
    y_masked = ma.masked_less_equal(y, 0)
    x_masked = ma.array(x, mask=y_masked.mask)

    # Rename for compactness
    x = x_masked.compressed()
    y = y_masked.compressed()

    # Simply ignore every point after y goes <= 0
#    try:
#        last = where(y<=0)[0][0]
#        x = x[:last]
#        y = y[:last]
#        plt.plot(x, y)
#    except IndexError:
#        # Do nothing if y never dips <= 0
#        pass

    a_num = sum(x*x*y)*sum(y*log(y)) - sum(x*y)*sum(x*y*log(y))
    b_num = sum(y)*sum(x*y*log(y)) - sum(x*y)*sum(y*log(y))
    den = sum(y)*sum(x*x*y) - sum(x*y)**2

    a = a_num / den
    b = b_num / den
    return exp(a), b, c


def guided_decay_fit(data_x, data_y):
    """
    Guided fit of a ringdown. Takes *data_x* and *data_y* as ``pint``
    Quantities with dimensions of time and voltage, respectively. Plots the
    data and asks user to manually crop to select the region to fit.

    It then does a rough linear fit to find initial parameters and performs
    a nonlinear fit.

    Finally, it plots the data with the curve fit overlayed and returns the
    full-width at half-max (FWHM) with units.
    """
    # Have user choose crop points
    plt.plot(data_x, data_y)
    cursor = Cursor(plt.gca(), useblit=True)
    cursor.horizOn = False
    (x1, y1), (x2, y2) = _ginput(2)
    plt.close()

    # Crop the data
    i1 = searchsorted(data_x.magnitude, x1)
    i2 = searchsorted(data_x.magnitude, x2)
    data_x = data_x[i1:i2]
    data_y = data_y[i1:i2]

    # Set t0 = 0 so that the amplitude 'a' doesn't blow up if we
    # have a large time offset
    t = data_x - data_x[0]

    def decay(x, a, b, c):
        return a*exp(b*x) + c

    # Do linear fit to get initial parameter estimate
    a0, b0, c0 = _linear_fit_decay(t.magnitude, data_y.magnitude)

    # Do nonlinear fit
    popt, pcov = curve_fit(decay, t.magnitude, data_y.magnitude, p0=[a0, b0, c0], maxfev=2000)
    a, b, c = popt
    tau = Q_(-1/b, t.units)
    fit = a * exp(-t/tau) + c
    final = Q_(c, data_y.units)

    t.ito('s')
    plt.plot(t, fit, 'b-', lw=2, zorder=3)
    plt.plot(t, data_y, 'gx')
    plt.title('Decay fit')
    plt.xlabel('Time (s)')
    plt.ylabel('Magnitude ({})'.format(data_y.units))
    plt.legend(['Fitted Curve', 'Data Trace'])
    plt.show()
    return tau, final


def guided_ringdown_fit(data_x, data_y):
    """
    Guided fit of a ringdown. Takes *data_x* and *data_y* as ``pint``
    Quantities with dimensions of time and voltage, respectively. Plots the
    data and asks user to manually crop to select the region to fit.

    It then does a rough linear fit to find initial parameters and performs
    a nonlinear fit.

    Finally, it plots the data with the curve fit overlayed and returns the
    full-width at half-max (FWHM) with units.
    """
    # Have user choose crop points
    plt.plot(data_x, data_y)
    cursor = Cursor(plt.gca(), useblit=True)
    cursor.horizOn = False
    (x1, y1), (x2, y2) = _ginput(2)
    plt.close()

    # Crop the data
    i1 = searchsorted(data_x.magnitude, x1)
    i2 = searchsorted(data_x.magnitude, x2)
    data_x = data_x[i1:i2]
    data_y = data_y[i1:i2]

    # Set t0 = 0 so that the amplitude 'a' doesn't blow up if we
    # have a large time offset
    t = data_x - data_x[0]
    amp = data_y / u.V

    def decay(x, a, b, c):
        return a*exp(b*x) + c

    # Do linear fit to get initial parameter estimate
    a0, b0, c0 = _linear_fit_decay(t.magnitude, amp.to('').magnitude)

    # Do nonlinear fit
    popt, pcov = curve_fit(decay, t.magnitude, amp.magnitude, p0=[a0, b0, c0], maxfev=2000)
    a, b, c = popt
    tau = Q_(-1/b, t.units)
    FWHM = (1 / (2*pi*tau)).to('MHz')

    fit = a * exp(-t/tau) + c

    t.ito('ns')
    plt.plot(t, fit, 'b-', lw=2, zorder=3)
    plt.plot(t, amp, 'gx')
    plt.title('Ringdown fit')
    plt.xlabel('Time (ns)')
    plt.ylabel('Transmission (arb. units)')
    plt.legend(['Fitted Curve', 'Data Trace'])
    plt.show()
    return FWHM


def guided_trace_fit(data_x, data_y, EOM_freq):
    """
    Guided fit of a cavity scan trace that has sidebands. Takes *data_x* and
    *data_y* as ``pint`` Quantities, and the EOM frequency *EOM_freq* can be
    anything that the ``pint.Quantity`` constructor understands, like an
    existing ``pint.Quantity`` or a string, e.g. ``'5 Mhz'``.

    It plots the data then asks the user to identify the three maxima by
    by clicking on them in left-to-right order. It then uses that input
    to estimate and then do a nonlinear fit of the parameters.

    Finally, it plots the data with the curve fit overlayed and returns the
    parameters in a map.

    The parameters are ``A0``, ``B0``, ``FWHM``, ``nu0``, and ``dnu``.
    """
    EOM_freq = Q_(EOM_freq)

    # Have user mark the three maxima
    plt.plot(data_x, data_y)
    plt.axis('tight')
    pts = _ginput(3)
    plt.close()

    (x1, y1), (x2, y2), (x3, y3) = ((x*u.s, y*u.V) for (x, y) in pts)
    scale_factor_x = 2*EOM_freq / (x3-x1)
    scale_factor_y = 1 / u.V

    # Scale the data into frequency space
    nu = data_x * scale_factor_x
    amp = data_y * scale_factor_y

    # Calculate the initial estimated parameters
    A0 = y2 * scale_factor_y
    B0 = (y1+y3)/2 * scale_factor_y
    nu0 = x2 * scale_factor_x
    dnu = EOM_freq
    y0 = 0 * u.dimensionless
    FWHM = _estimate_FWHM_pint(nu, amp, A0/2, nu0-dnu/2, nu0, nu0+dnu/2)

    # Do a curve fit to get new params
    popt, pcov = curve_fit(triple_lorentzian, nu, amp, p0=(A0, B0, FWHM, nu0, dnu, y0))
    A0, B0, FWHM, nu0, dnu, y0 = popt

    # Put params in format needed for param_plot
    params = {
        'A0': A0,
        'B0': B0,
        'FWHM': FWHM,
        'nu0': nu0,
        'dnu': dnu,
        'y0': y0
    }

    # Plot the data and fit on a param_plot
    plt.plot(nu, amp, 'gx', nu, triple_lorentzian(nu, **params), 'b-', linewidth=2)
    plt.xlim([(nu0-2*dnu).magnitude, (nu0+2*dnu).magnitude])
    plt.title('Cavity Trace Fit')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Transmission (arb. units)')
    plt.legend(['Data Trace', 'Fitted Curve'])
    plt.text(0, 1, 'FWHM = {:.2f}'.format(FWHM), ha='left', va='top',
             transform=plt.gca().transAxes)
    plt.show()

    return params
