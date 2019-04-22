# -*- coding: utf-8 -*-
# Copyright 2019 Nate Bogdanowicz
from collections import defaultdict
import numpy as np
import visa

from ..util import visa_context
from ... import Q_

method_registry = defaultdict(list)


def patch_class(cls):
    """Patch a class with its async methods."""
    for method in method_registry[cls.__name__]:
        setattr(cls, method.__name__, method)


def method_of(clsname):
    def wrap(func):
        method_registry[clsname].append(func)
    return wrap


@method_of('TekScope')
def async_get_data(self, channel=1, width=2):
    """Retrieve a trace from the scope asynchronously.

    Pulls data from channel `channel` and returns it as a tuple ``(t,y)``
    of unitful arrays. Python >= 3.3 only.

    Use within generators/coroutines like this::
        t, y = yield from scope.async_get_data(channel=1)


    Parameters
    ----------
    channel : int, optional
        Channel number to pull trace from. Defaults to channel 1.
    width : int, optional
        Number of bytes per sample of data pulled from the scope. 1 or 2.

    Returns
    -------
    t, y : pint.Quantity arrays
        Unitful arrays of data from the scope. ``t`` is in seconds, while
        ``y`` is in volts.
    """
    if width not in (1, 2):
        raise ValueError('width must be 1 or 2')

    with self.transaction():
        self.write("data:source ch{}".format(channel))
        try:
            # scope *should* truncate this to record length if it's too big
            stop = self.max_waveform_length
        except AttributeError:
            stop = 1000000
        self.write("data:width {}", width)
        self.write("data:encdg RIBinary")
        self.write("data:start 1")
        self.write("data:stop {}".format(stop))

    #self.resource.flow_control = 1  # Soft flagging (XON/XOFF flow control)
    raw_data_y = yield from self._async_read_curve(width=width)
    raw_data_x = np.arange(1, len(raw_data_y)+1)

    # Get scale and offset factors
    wp = yield from self._async_waveform_params()
    x_units = self._tek_units(wp['xun'])
    y_units = self._tek_units(wp['yun'])

    data_x = Q_((raw_data_x - wp['pt_o'])*wp['xin'] + wp['xze'], x_units)
    data_y = Q_((raw_data_y - wp['yof'])*wp['ymu'] + wp['yze'], y_units)

    return data_x, data_y


@method_of('TekScope')
def _async_read_curve(self, width):
    with self.resource.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT),\
        visa_context(self.resource, timeout=10000, read_termination=None,
                     end_input=visa.constants.SerialTermination.none):

        self.write("curve?")
        async_read_chunk = self.resource._async_read_chunk

        # NB: Must take slice of bytes, to keep from autoconverting to int
        header_width = int((yield from async_read_chunk(2))[0][1:])
        num_bytes = int((yield from async_read_chunk(header_width))[0])
        buf = bytearray(num_bytes)
        cursor = 0

        while cursor < num_bytes:
            raw_bin, _ = yield from async_read_chunk(num_bytes-cursor)
            buf[cursor:cursor+len(raw_bin)] = raw_bin
            cursor += len(raw_bin)

    yield from self.resource._async_read_raw()  # Eat termination

    num_points = int(num_bytes // width)
    dtype = '>i{:d}'.format(width)
    return np.frombuffer(buf, dtype=dtype, count=num_points)


@method_of('TekScope')
def _async_waveform_params(self):
    self.write('wfmoutpre?')
    msg = yield from self.resource.async_read()
    return self._unpack_wfm_params(msg.split(';'))
