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

def plot_profile(q_start_t_r, q_start_s_r, lambda0, elems, cyclical=False, names=tuple(), clipping=None, show_axis=False, show_waists=False, zeroat=0):
    """
    Plot tangential and sagittal beam profiles. 

    Parameters
    ----------
    q_start_t_r, q_start_s_r : complex
        Reciprocal beam parameters for the tangential and sagittal components.
    lambda0 : float
        Vacuum wavelength of the beam.
    elems : list of optical elements
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
    zs, profs_t, RoC = get_profiles(q_start_t_r, lambda0, 'tangential', elems, clipping, zeroat)
    zs, profs_s, RoC = get_profiles(q_start_s_r, lambda0, 'sagittal', elems, clipping, zeroat)
    
    scale = 3
    fig, ax = subplots(figsize=(4*scale,3*scale))
    margin = .0002e3
    ax.set_xlim([zs[0][0]*1e3-margin, zs[-1][-1]*1e3+margin])
    
    z = np.concatenate(zs)
    prof_t = np.concatenate(profs_t)
    prof_s = np.concatenate(profs_s)
    ax.plot(z*1e3, prof_t*1e3, color='b', label='Tangential beam', linewidth=3)
    ax.plot(z*1e3, prof_s*1e3, color='r', label='Sagittal beam', linewidth=3)

    if show_waists:
        # Mark waists
        # Should use scipy.signal.argrelextrema, but it's not available before 0.11
        t_waist_indices = _argrelmin(prof_t)
        s_waist_indices = _argrelmin(prof_s)
        for i in t_waist_indices:
            ax.annotate('{:.3f} mm'.format(prof_t[i]*1e3), (z[i]*1e3, prof_t[i]*1e3), xytext=(0,-30), textcoords='offset points', ha='center', arrowprops=dict(arrowstyle="->"))
        for i in s_waist_indices:
            ax.annotate('{:.3f} mm'.format(prof_s[i]*1e3), (z[i]*1e3, prof_s[i]*1e3), xytext=(0,-30), textcoords='offset points', ha='center', arrowprops={'arrowstyle':'->'})
     
    ax.set_xlabel('Position [mm]')
    if clipping is not None:
        ylabel = 'Distance from beam axis for clipping of {:.1e} [mm]'.format(clipping)
    else:
        ylabel = 'Spot size [mm]'
    ax.set_ylabel(ylabel)
    #ax.legend()

    if show_axis:
        ax.set_ylim(bottom=0)
    ax.set_autoscaley_on(False)
    
    if cyclical:
        zs.append(zs[-1][-1:])
        names.append(names[0])
        profs_t.append(profs_t[0])
        profs_s.append(profs_s[0])

    # Plot boundary lines and names (if provided)
    for z, prof_t, prof_s, name in zip(zs, profs_t, profs_s, names):
        z = z*1e3
        ax.vlines([z[0]], ax.get_ylim()[0], ax.get_ylim()[1], linestyle='dashed',
                  linewidth=3, color=(.5,.5,.5), antialiased=True)

        # Get relevant y boundaries
        ylim0,ylim1 = ax.get_ylim()
        if prof_t[0] < prof_s[0]:
            pmin, pmax = prof_t[0]*1e3, prof_s[0]*1e3
        else:
            pmin, pmax = prof_s[0]*1e3, prof_t[0]*1e3

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
        ax.text(z[0], margin, name, rotation='vertical',
                ha='center', va=va, size='xx-large', backgroundcolor='w')

def plot_profile_and_RoC(q_start_r, lambda0, elems, cyclical=False, names=tuple(), segments=None, clipping=None):
    zs, profiles, RoCs = get_profiles(q_start_r, lambda0, 'sagittal', elems, clipping)
    if segments:
        zs = zs[segments]
        profiles = profiles[segments]
        RoCs = RoCs[segments]
    
    scale = 3
    fig, ax1 = subplots(figsize=(4*scale, 3*scale))
    ax2 = ax1.twinx()
    ax1.set_xlim([0, zs[-1][-1]*1e3])
    
    for z, profile, RoC in zip(zs, profiles, RoCs):
        ax1.plot(z*1e3, profile*1e3, color='b', label='Spot Size')
        ax2.plot(z*1e3, RoC*1e3, color='g', label='Radius of Curvature')
    
    ax1.set_xlabel('Distance from exit mirror [mm]')
    ax1.set_ylabel('Spot size [mm]')
    ax2.set_ylabel('Radius [mm]')
    
    factor = 100
    bot = min(ax1.get_ylim()[0], ax2.get_ylim()[0]/factor)
    top = max(ax1.get_ylim()[1], ax2.get_ylim()[1]/factor)
    ax1.set_ylim(bot, top)
    ax2.set_ylim(bot*factor, top*factor)
    ax1.set_autoscaley_on(False)
    ax2.set_autoscaley_on(False)
    ax1.legend(loc=4)
    ax2.legend(loc=1)
    
    f = interp1d(RoCs[0], zs[0])
    ax2.hlines(300, ax1.get_xlim()[1], f(300e-3)*1e3, linestyle='dashed')
    ax2.vlines(f(300e-3)*1e3, ax1.get_ylim()[0], 300, linestyle='dashed')
    ax1.plot(299.3, 1.5, 'D', color='r')
    
    for z, name in zip(zs, names):
        ax1.vlines([z[0]], ax1.get_ylim()[0], ax1.get_ylim()[1], linestyle='dashed', linewidth=1, color=(.5,.5,.5), antialiased=True)
        margin = (ax1.get_ylim()[1]-ax1.get_ylim()[0])/100*2
        ax1.text(z[0], ax1.get_ylim()[0]+margin, name, rotation='vertical', ha='center', va='bottom', size='xx-large', backgroundcolor='w')
