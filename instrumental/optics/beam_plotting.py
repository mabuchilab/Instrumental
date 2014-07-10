# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz

import numpy as np
from scipy.interpolate import interp1d
from matplotlib.pyplot import subplots
from beam_tools import *

def _flatten_list_of_lists(li):
    flattened = []
    for el in li:
        flattened.extend(el)
    return flattened

def _argrelmin(data):
    """ Finds indices of relative minima. Doesn't count first and last points
    as minima """
    args = []
    curmin = data[0] # This keeps the first point from being included
    curminarg = None
    for i,num in enumerate(data):
        if num < curmin:
            curmin = num
            curminarg = i
        elif num > curmin and curminarg is not None:
            # Once curve starts going up, we know we've found a minimum
            args.append(curminarg)
            curminarg = None
    return args


def _magify(outer, units):
    return [inner.to(units).magnitude for inner in outer]


def plot_profile(q_start_t_r, q_start_s_r, lambda0, elems, cyclical=False,
                 names=tuple(), clipping=None, show_axis=False,
                 show_waists=False, zeroat=0, zunits='mm', runits='um'):
    """
    Plot tangential and sagittal beam profiles. 

    Parameters
    ----------
    q_start_t_r, q_start_s_r : complex Quantity objects
        Reciprocal beam parameters for the tangential and sagittal components.
        They have units of 1/[length].
    lambda0 : Quantity
        Vacuum wavelength of the beam in units of [length].
    elems : list of OpticalElements
        Ordered list of optical elements through which the beams pass and are
        plotted.

    Other Parameters
    ----------------
    cyclical : bool
        Whether `elems` loops back on itself, i.e. it forms a cavity where
        the last element is immediately before the first element. Used for
        labelling the elements correctly if `names` is used.
    names : list or tuple of str
        Strings used to label the non-`Space` elements on the plot. Vertical
        lines will be used to denote the element's position.
    clipping : float
        Clipping loss level to plot. Normally, the beam profile plotted is
        the usual spot size. However, if `clipping` is given, the profile
        indicates the distance from the beam axis at which knife-edge clipping
        power losses are equal to `clipping`.
    show_axis : bool
        If `show_axis` is `True`, sets the ylim to include the beam axis, i.e.
        y=0. Otherwise, y limits are automatically set by matplotlib.
    show_waists : bool
        If `True`, marks beam waists on the plot and labels their size.
    zeroat : int
        The *index* of the element in `elems` that we should consider as z=0.
        Useful for looking at distances from some element that's in the middle
        of the plot.
    """
    zs, profs_t, RoCs = get_profiles(q_start_t_r, lambda0, 'tangential', elems,
                                    clipping, zeroat)
    zs, profs_s, RoCs = get_profiles(q_start_s_r, lambda0, 'sagittal', elems,
                                    clipping, zeroat)

    # Convert lists of Quantity-arrays
    zs_mag = _magify(zs, zunits)
    profs_t_mag = _magify(profs_t, runits)
    profs_s_mag = _magify(profs_s, runits)
    #RoC_mag = _magify(RoC, runits)

    fig_scale = 3
    fig, ax = subplots(figsize=(4*fig_scale,3*fig_scale))
    margin = .0002e3
    ax.set_xlim([zs_mag[0][0]-margin, zs_mag[-1][-1]+margin])

    # Concatenate list into a single Quantity-array
    z_mag = np.concatenate(zs_mag)
    prof_t_mag = np.concatenate(profs_t_mag)
    prof_s_mag = np.concatenate(profs_s_mag)

    ax.plot(z_mag, prof_t_mag, color='b', label='Tangential beam', linewidth=3)
    ax.plot(z_mag, prof_s_mag, color='r', label='Sagittal beam', linewidth=3)

    if show_waists:
        # Mark waists
        # Should use scipy.signal.argrelextrema, but it's not available before 0.11
        t_waist_indices = _argrelmin(prof_t_mag)
        s_waist_indices = _argrelmin(prof_s_mag)
        for i in t_waist_indices:
            ax.annotate('{:.3f} {}'.format(prof_t_mag, runits),
                        (z_mag[i], prof_t_mag[i]),
                        xytext=(0,-30), textcoords='offset points',
                        ha='center', arrowprops=dict(arrowstyle="->"))
        for i in s_waist_indices:
            ax.annotate('{:.3f} {}'.format(prof_s_mag, runits),
                        (z_mag[i], prof_s_mag[i]), xytext=(0,-30),
                        textcoords='offset points', ha='center',
                        arrowprops={'arrowstyle':'->'})
     
    ax.set_xlabel('Position [{}]'.format(zunits))
    if clipping is not None:
        ylabel = ('Distance from beam axis for clipping of ' +
                  '{:.1e} [{}]'.format(clipping, runits))
    else:
        ylabel = 'Spot size [{}]'.format(runits)
    ax.set_ylabel(ylabel)
    #ax.legend()

    if show_axis:
        ax.set_ylim(bottom=0)
    ax.set_autoscaley_on(False)
    
    if cyclical:
        zs_mag.append(zs_mag[-1][-1:])
        names.append(names[0])
        profs_t_mag.append(profs_t_mag[0])
        profs_s_mag.append(profs_s_mag[0])

    # Plot boundary lines and names (if provided)
    for z_mag, prof_t_mag, prof_s_mag, name in zip(zs_mag, profs_t_mag,
                                                   profs_s_mag, names):
        ax.vlines([z_mag[0]], ax.get_ylim()[0], ax.get_ylim()[1],
                  linestyle='dashed', linewidth=3, color=(.5,.5,.5),
                  antialiased=True)

        # Get relevant y boundaries
        ylim0, ylim1 = ax.get_ylim()
        if prof_t_mag[0] < prof_s_mag[0]:
            pmin, pmax = prof_t_mag[0], prof_s_mag[0]
        else:
            pmin, pmax = prof_s_mag[0], prof_t_mag[0]

        region = np.argmax([pmin-ylim0, pmax-pmin, ylim1-pmax])
        if region==0:
            margin = ylim0
            va = 'bottom'
        elif region==1:
            margin = pmin + (pmax-pmin)*0.5
            va = 'center'
        else:
            margin = ylim1 - (ylim1-pmax)*0.2
            va = 'top'
        ax.text(z_mag[0], margin, name, rotation='vertical', ha='center',
                va=va, size='xx-large', backgroundcolor='w')
