# -*- coding: utf-8 -*-
# Copyright 2013-2014 Nate Bogdanowicz
"""
Module that provides unit-aware plotting functions that can be used as a
drop-in replacement for matplotlib.pyplot.

Also acts as a repository for useful plotting tools, like slider-plots.
"""

from collections import OrderedDict, Mapping
import itertools

import numpy as np
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.transforms import Bbox
from matplotlib.cbook import is_string_like

from . import u, Q_


def _get_line_tups(*args):
    """
    Helper func to parse input to plot()
    """
    # Assume all args are either data or format strings, plt.plot will
    # deal with raising exceptions.
    # A line's arguments consist of [x], y, [fmt]
    lines = []
    while args:
        fmt = ''
        y = Q_(args[0])
        if len(args) > 1:
            if is_string_like(args[1]):
                fmt = args[1]
                x = Q_(np.arange(y.shape[0], dtype=float))
                args = args[2:]
            else:
                x = y
                y = Q_(args[1])
                if len(args) > 2 and is_string_like(args[2]):
                    fmt = args[2]
                    args = args[3:]
                else:
                    args = args[2:]
        else:
            x = Q_(np.arange(y.shape[0], dtype=float))
            args = args[1:]
        lines.append((x, y, fmt))
    return lines


def _pluralize(unit_name):
    if unit_name[-1] in ['s', 'z']:
        return unit_name
    return unit_name + 's'


def _to_engineering_notation(x):
    high = np.max(x)
    low = np.min(x)
    max_abs = max(np.abs(low), np.abs(high))
    power = int(np.log10(max_abs.to_base_units().magnitude) // 3)*3


def xlabel(s, *args, **kwargs):
    """Quantity-aware wrapper of pyplot.xlabel

    Automatically adds parenthesized units to the end of `s`.
    """
    ax = gca()
    try:
        units = _pluralize(str(ax.xunits))
        s += " ({})".format(units)
    except AttributeError:
        pass
    plt.xlabel(s, *args, **kwargs)


def ylabel(s, *args, **kwargs):
    """Quantity-aware wrapper of pyplot.ylabel.

    Automatically adds parenthesized units to the end of `s`.
    """
    ax = gca()
    try:
        units = _pluralize(str(ax.yunits))
        s += " ({})".format(units)
    except AttributeError:
        pass
    plt.ylabel(s, *args, **kwargs)


def plot(*args, **kwargs):
    """Quantity-aware wrapper of pyplot.plot"""
    line_tups = _get_line_tups(*args)
    xunits = line_tups[0][0].units
    yunits = line_tups[0][1].units

    # Scale the arrays to all use the same units
    scaled_line_tups = []
    for line_tup in _get_line_tups():
        x, y, fmt = line_tup
        scaled_line_tups.append((x.to(xunits), y.to(yunits), fmt))

    # Flatten line_tups
    arglist = list(itertools.chain(*line_tups))

    lines = plt.plot(*arglist, **kwargs)
    ax = plt.gca()
    ax.xunits = xunits
    ax.yunits = yunits

    for line, line_tup in zip(lines, scaled_line_tups):
        x, y, fmt = line_tup
        line.qx = x
        line.qy = y

    return lines


def _bbox_from_fontsize(left, bottom, right, height, fig=None):
    """
    Specify left, bottom, right padding and height in units of font-size
    """
    if not fig:
        fig = plt.gcf()

    fig_inches = fig.get_size_inches()
    fig_w_in, fig_h_in = fig_inches
    fontsize_rel_h = 12.0/(72*fig_h_in)
    fontsize_rel_w = 12.0/(72*fig_w_in)

    box_left_rel = left*fontsize_rel_w
    box_bottom_rel = bottom*fontsize_rel_h
    box_right_rel = 1 - right*fontsize_rel_w
    box_height_rel = height*fontsize_rel_h

    return Bbox.from_extents(box_left_rel,
                             box_bottom_rel,
                             box_right_rel,
                             box_bottom_rel+box_height_rel)


def _bbox_fixed_margin(left, bottom, right, top, fig=None):
    if not fig:
        fig = plt.gcf()

    fig_inches = fig.get_size_inches()
    fig_w_in, fig_h_in = fig_inches
    fontsize_rel_h = 12.0/(72*fig_h_in)
    fontsize_rel_w = 12.0/(72*fig_w_in)

    box_left_rel = left*fontsize_rel_w
    box_bottom_rel = bottom*fontsize_rel_h
    box_right_rel = 1 - right*fontsize_rel_w
    box_top_rel = 1 - top*fontsize_rel_h

    return Bbox.from_extents(box_left_rel,
                             box_bottom_rel,
                             box_right_rel,
                             box_top_rel)


def _initialize_range_params(param_dict):
    """
    Helper function that initializes the range-related parameters
    """
    pd = param_dict

    init = pd.get('init', 1)
    pd.setdefault('min', min(0.8*init, 1.2*init))
    pd.setdefault('max', max(0.8*init, 1.2*init))
    pd.setdefault('init', (pd['max']-pd['min'])*0.5 + pd['min'])

    if 'pm' in pd and 'init' in pd:
        pd['min'] = pd['init'] - abs(pd['pm'])
        pd['max'] = pd['init'] + abs(pd['pm'])
    elif 'pm_pct' in pd and 'init' in pd:
        diff = abs(pd['init']*pd['pm_pct']/100.0)
        pd['min'] = pd['init'] - diff
        pd['max'] = pd['init'] + diff
    else:
        if 'min' in pd:
            if 'max' in pd:
                if 'init' not in pd:
                    pd['init'] = (pd['max'] - pd['min'])*0.5
                else:
                    pass  # Add check if in range, clip or expand if necessary
            else:
                if 'init' in pd:
                    # Add check that init > min
                    pd['max'] = pd['min'] + 2*(pd['init'] - pd['min'])
                else:
                    pd['init'] = max(pd['min']/0.8, pd['min']/1.2)
                    pd['max'] = max(pd['init']*1.2, pd['init']*0.8)
        else:
            if 'max' in pd:
                if 'init' in pd:
                    # Add check that init < max
                    pd['min'] = pd['max'] - 2*(pd['max'] - pd['init'])
                else:
                    pd['init'] = min(pd['max']/1.2, pd['max']/0.8)
                    pd['min'] = min(pd['init']*0.8, pd['init']*1.2)
            else:
                if 'init' in pd:
                    pd['min'] = min(pd['init']*0.8, pd['init']*1.2)
                    pd['max'] = max(pd['init']*1.2, pd['init']*0.8)
                else:
                    pd['min'] = 0.0
                    pd['init'] = 0.5
                    pd['max'] = 1.0

    try:
        units = pd['init'].units
        pd['units'] = pd['init'].units
        pd['init'] = pd['init'].magnitude
        pd['min'] = pd['min'].to(units).magnitude
        pd['max'] = pd['max'].to(units).magnitude
    except AttributeError:
        pass


def _initialize_params(params):
    """
    Helper function to ensure 'params' is in a nice state for later use.
    """
    if 'order' in params:
        # Sort using provided key ordering
        p = OrderedDict( ((k, params[k]) for k in params['order']) )
    else:
        # Order alphabetically by key name
        p = OrderedDict(sorted(params.items(), key=lambda t: t[0]))

    for k, pd in p.iteritems():

        # Allow shorhand where only initial value is specified
        if not isinstance(pd, Mapping):
            pd = {'init': pd}
            p[k] = pd

        _initialize_range_params(pd)

        pd.setdefault('label', k.title())

    return p


# Slider size parameters
slider_height = 0.8
slider_pad_top = 0.1
slider_pad_bot = 0.1
slider_pad_left = 5.0
slider_pad_right = 5.0
slider_fullheight = slider_pad_bot + slider_height + slider_pad_top


def _bbox_with_margins(left, bottom, right, top):
    fig = plt.gcf()
    x0 = fig.bbox.x0 + left
    y0 = fig.bbox.y0 + bottom
    x1 = fig.bbox.x1 - right
    y1 = fig.bbox.y1 - top
    return Bbox([[x0, y0], [x1, y1]]).transformed(fig.transFigure.inverted())


def _slider_bbox(i, fig=None):
    return _bbox_from_fontsize(slider_pad_left,
                               1+i*slider_fullheight,
                               slider_pad_right,
                               slider_height,
                               fig)


def _main_ax_bbox(ax, i, fig=None):
    left = 3.0 + (2 if ax.get_ylabel() else 0)
    right = 1.4
    bottom = 2.0 + (2 if ax.get_xlabel() else 0) + i*slider_fullheight
    top = 1.4 + (1 if ax.get_title() else 0)
    return _bbox_fixed_margin(left, bottom, right, top, fig)


def _unitify(param_dict, value):
    """
    Helper function to create a pint.Quantity from the dict of a given
    parameter. Returns just the value if units weren't provided.
    """
    if 'units' in param_dict:
        return u.Quantity(value, param_dict['units'])
    return value


def param_plot(x, func, params, **kwargs):
    """
    Plot a function with user-adjustable parameters.

    Parameters
    ----------
    x : array_like
        Independent (x-axis) variable.
    func : function
        Function that takes as its first argument an independent variable and
        as subsequent arguments takes parameters. It should return an output
        array the same dimension as `x`, which is plotted as the y-variable.
    params : dict
        Dictionary whose keys are strings named exactly as the parameter
        arguments to `func` are. [More info on options]

    Returns
    -------
    final_params : dict
        A dict whose keys are the same as `params` and whose values correspond
        to the values selected by the slider. `final_params` will continue to
        change until the figure is closed, at which point it has the final
        parameter values the user chose. This is useful for hand-fitting
        curves.
    """

    params = _initialize_params(params)
    flat_params = {k: _unitify(v, v['init']) for k, v in params.iteritems()}

    # Set up figure and axes that we'll plot on
    fig = plt.figure()
    ax0 = fig.add_axes([0, 0, 1, 1])

    l, = ax0.plot(x, func(x, **flat_params), **kwargs)

    # Function for redrawing curve when a parameter value is changed
    def update(val):
        param_args = {k: _unitify(v, v['slider'].val) for k, v in params.iteritems()}
        l.set_ydata(func(x, **param_args))
        fig.canvas.draw_idle()

        # Update values in flat_params so end user can get their final values
        flat_params.update(param_args)

    # Create axes and sliders for each parameter
    for i, (name, vals) in enumerate(params.iteritems()):
        ax = plt.axes(_slider_bbox(i).bounds)
        slider = Slider(ax, vals['label'], vals['min'], vals['max'], vals['init'])
        slider.on_changed(update)
        vals['ax'] = ax
        vals['slider'] = slider

    # Function for auto-scaling sliders to (ironically) keep them fixed
    def resize_func(event):
        ax0.set_position(_main_ax_bbox(ax0, len(params), fig).bounds)
        for i, val in enumerate(params.itervalues()):
            box = _slider_bbox(i)
            val['ax'].set_position(box)

    fig.canvas.mpl_connect('resize_event', resize_func)

    # Set current axes to the one you'd expect
    plt.sca(ax0)
    return flat_params
