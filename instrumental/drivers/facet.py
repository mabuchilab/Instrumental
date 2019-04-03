# -*- coding: utf-8 -*-
# Copyright 2013-2019 Nate Bogdanowicz

from __future__ import division
from past.builtins import basestring

import numbers
from collections import Mapping, namedtuple

from ..log import get_logger
from .. import u, Q_
from .util import to_quantity

log = get_logger(__name__)


ChangeEvent = namedtuple('ChangeEvent', ['name', 'old', 'new'])


class FacetGroup(object):
    """A collection of an instrument's FacetData objects"""
    def __init__(self, facet_data_list):
        for facet_data in facet_data_list:
            setattr(self, facet_data.facet.name, facet_data)
        self._names = [fd.facet.name for fd in facet_data_list]

    def __repr__(self):
        return "<FacetGroup({})>".format(', '.join(name for name in self._names))

    def __getitem__(self, key):
        if key not in self._names:
            raise KeyError
        return self.__dict__[key]


class FacetData(object):
    """Per-instance Facet data"""
    def __init__(self, parent_facet, owner):
        self.dirty = True
        self.cached_val = None
        self.observers = []
        self.facet = parent_facet
        self.owner = owner

    def __repr__(self):
        return "<FacetData '{}'>".format(self.facet.name)

    def observe(self, callback):
        """Add a callback to observe changes in a facet's value

        The callback should be a callable accepting a ``ChangeEvent`` as its only argument. This
        ``ChangeEvent`` is a namedtuple with ``name``, ``old``, and ``new`` fields. ``name`` is the
        facet's name, ``old`` is the old value, and ``new`` is the new value.
        """
        self.observers.append(callback)

    def get_value(self):
        return self.facet.get_value(self.owner)

    def set_value(self, value):
        self.facet.set_value(self.owner, value)

    def create_widget(self, parent=None):
        if self.facet.type == float:
            if self.facet.units:
                from ..gui import UDoubleSpinBox
                w = UDoubleSpinBox(parent, units=self.facet.units)
                if self.cached_val is not None:
                    w.setUValue(self.cached_val)
                def set_widget_value(event):
                    w.setUValue(event.new)
                self.observe(set_widget_value)
                w.uValueChanged.connect(self.set_value)
            else:
                from ..gui import QDoubleSpinBox
                w = QDoubleSpinBox(parent)
            return w
        raise TypeError("Facet type '{}' is not associated with a widget "
                        "type".format(self.facet.type))


class Facet(object):
    """Property-like class representing an attribute of an instrument.

    Parameters
    ----------
    fget : callable, optional
        A function to be used for getting the facet's value.
    fset : callable, optional
        A function to be used for setting the facet's value.
    doc : str, optional
        Docstring to describe the facet
    cached : bool, optional
        Whether the facet should use caching. If True, the repeated writes of the same value will
        only write to the instrument once, while repeated reads of a value will only query the
        instrument once. Therefore, one should be careful to use caching only when it makes sense.
        Caching can be disabled on a per-get or per-set basis by using the `use_cache` parameter to
        `get_value()` or `set_value()`.
    type : callable, optional
        Type of the outward-facing value of the facet. Typically an actual type like `int`, but can
        be any callable that converts a value to the proper type.
    units : pint.Units or corresponding str
        Physical units of the facet's value. Used for converting both user input (when setting) and
        the output of fget (when getting).
    value : dict-like, optional
        A map from 'external' values to 'internal' facet values. Used internally to convert input
        values for use with fset and to convert values returned by fget into 'nice' values fit force
        user consumption.
    limits : sequence, optional
        Limits specified in `[stop]`, `[start, stop]`, or `[start, stop, step]` format. When given,
        raises a `ValueError` if a user tries to set a value that is out of range. `step`, if given,
        is used to round an in-range value before passing it to fset.
    """
    def __init__(self, fget=None, fset=None, doc=None, cached=False, type=None, units=None,
                 value=None, limits=None, name=None):
        if fget is not None:
            self.name = fget.__name__

        self.fget = fget
        self.fset = fset

        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

        self.cacheable = cached
        self.type = type
        self.units = None if units is None else u.parse_units(units)
        self.name = name  # This is auto-filled by InstrumentMeta.__new__ later
        self._set_limits(limits)

        if value is None:
            self.values = None
            self.in_map = None
            self.out_map = None
        elif isinstance(value, Mapping):
            self.values = set(value)
            self.in_map = value
            self.out_map = {v:k for k,v in value.items()}
        else:
            self.values = set(value)
            self.in_map = None
            self.out_map = None

    def __repr__(self):
        return "<Facet '{}'>".format(self.name)

    def _set_limits(self, limits):
        if limits is not None:
            for limit in limits:
                if limit is not None and not isinstance(limit, (numbers.Number, basestring)):
                    raise ValueError('Facet limits must be raw numbers, strings, or None')

        if limits is None:
            self.limits = (None, None, None)
        elif len(limits) == 1:
            self.limits = (0, limits[0], None)
        elif len(limits) == 2:
            self.limits = (limits[0], limits[1], None)
        elif len(limits) == 3:
            self.limits = (limits[0], limits[1], limits[2])
        else:
            raise ValueError("`limits` must be a sequence of length 1 to 3")

    def instance(self, obj):
        """Get the FacetData associated with `obj`"""
        try:
            return obj.__dict__[self.name]
        except KeyError:
            inst = FacetData(self, obj)
            obj.__dict__[self.name] = inst
            return inst

    def conv_set(self, value):
        """Convert nice value to representation that fset takes"""
        if isinstance(value, Q_):
            value = value.magnitude
        #if self.type is not None:
        #    value = self.type(value)
        if self.in_map:
            value = self.in_map[value]
        return value

    def conv_get(self, value):
        """Convert what fget returns to a nice output value"""
        if self.out_map:
            value = self.out_map[value]
        if self.type is not None:
            value = self.type(value)
        if self.units is not None:
            if isinstance(value, Q_):
                value = value.to(self.units)
            else:
                value = Q_(value, self.units)
        return value

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.get_value(obj)

    def get_value(self, obj, use_cache=True):
        if self.fget is None:
            raise AttributeError

        instance = self.instance(obj)

        if not (self.cacheable and use_cache) or instance.dirty:
            log.debug('Getting value of facet %s', self.name)
            instance.cached_val = self.conv_get(self.fget(obj))
            instance.dirty = False
        else:
            log.debug('Using cached value of facet %s', self.name)

        log.debug('Facet value was %s', instance.cached_val)
        return instance.cached_val

    def __set__(self, obj, qty):
        self.set_value(obj, qty)

    def convert_user_input(self, value, obj):
        """Validate and convert an input value to its 'external' form"""
        if self.units is not None:
            q = to_quantity(value).to(self.units)
            return Q_(self.convert_raw_input(q.magnitude, obj), q.units)
        else:
            return self.convert_raw_input(value, obj)

    def convert_raw_input(self, input_value, obj):
        value = input_value if self.type is None else self.type(input_value)
        return self.check_limits(value, obj)

    def _load_limits(self, obj):
        return tuple((getattr(obj, l) if isinstance(l, basestring) else l)
                     for l in self.limits)

    def check_limits(self, value, obj):
        """Check raw value (magnitude) against the Facet's limits"""
        start, stop, step = self._load_limits(obj)
        if start is not None and value < start:
            raise ValueError("Value below lower limit of {}".format(
                Q_(start, self.units) if self.units else start))
        if stop is not None and value > stop:
            raise ValueError("Value above upper limit of {}".format(
                Q_(stop, self.units) if self.units else stop))

        if step is not None:
            offset = value - start
            if offset % step != 0:
                new_value = start + int(round(offset / step)) * step
                log.debug("Coercing value from %s to %s due to limit step", value, new_value)
                return new_value

        return value

    def set_value(self, obj, value, use_cache=True):
        if self.fset is None:
            raise AttributeError("Cannot set a read-only Facet")

        instance = self.instance(obj)
        value = self.convert_user_input(value, obj)

        if not (self.cacheable and use_cache) or instance.cached_val != value:
            log.info('Setting value of facet %s', self.name)
            self.fset(obj, self.conv_set(value))
            change = ChangeEvent(name=self.name, old=instance.cached_val, new=value)
            for callback in instance.observers:
                callback(change)
        else:
            log.info('Skipping set of facet %s, cached value matches', self.name)

        instance.cached_val = value
        log.info('Facet value is %s', value)

    def __call__(self, fget):
        return self.getter(fget)

    def getter(self, fget):
        self.fget = fget
        if not self.__doc__:
            self.__doc__ = fget.__doc__
        return self

    def setter(self, fset):
        self.fset = fset
        if not self.__doc__:
            self.__doc__ = fset.__doc__
        return self


class AbstractFacet(Facet):
    __isabstractmethod__ = True


class ManualFacet(Facet):
    def __init__(self, doc=None, cached=False, type=None, units=None, value=None, limits=None,
                 name=None, save_on_set=True):
        Facet.__init__(self, self._manual_fget, self._manual_fset, doc=doc, cached=cached,
                       type=type, units=units, value=value, limits=limits, name=name)
        self.save_on_set = save_on_set

    def _manual_fget(self, owner):
        inst = self.instance(owner)
        try:
            return inst._manual_value
        except AttributeError:
            return self._default_value()

    def _manual_fset(self, owner, value):
        self.instance(owner)._manual_value = value
        if self.save_on_set and getattr(owner, '_alias', None):
            owner._save_state()  # Will raise exception if _alias undefined

    def _default_value(self):
        if self.units:
            return Q_(0, self.units)
        return None  # FIXME


def MessageFacet(get_msg=None, set_msg=None, convert=None, **kwds):
    """Convenience function for creating message-based Facets.

    Creates `fget` and `fset` functions that are passed to `Facet`, based on message templates.
    This is primarily used for writing your own Facet-creating helper functions for message-based
    drivers that have a unique message format. For standard SCPI-style messages, you can use
    `SCPI_Facet()` directly.

    This is for use with `VisaMixin`, as it assumes the instrument has `write` and `query` methods.

    Parameters
    ----------
    get_msg : str, optional
        Message used to query the facet's value. If omitted, getting is unsupported.
    set_msg : str, optional
        Message used to set the facet's value. This string is filled in with
        `set_msg.format(value)`, where value is the user-given value being set.
    convert : function or callable
        Function that converts both the string returned by querying the instrument and the set-value
        before it is passed to `str.format()`. Usually something like `int` or `float`.
    **kwds :
        Any other keywords are passed along to the `Facet` constructor
    """

    if get_msg is None:
        fget = None
    elif convert:
        def fget(obj):
            return convert(obj.query(get_msg))
    else:
        def fget(obj):
            return obj.query(get_msg)

    if set_msg is None:
        fset = None
    elif convert:
        def fset(obj, value):
            obj.write(set_msg.format(convert(value)))
    else:
        def fset(obj, value):
            obj.write(set_msg.format(value))

    return Facet(fget, fset, **kwds)


def SCPI_Facet(msg, convert=None, readonly=False, **kwds):
    """Facet factory for use in VisaMixin subclasses that use SCPI messages

    Parameters
    ----------
    msg : str
        Base message used to create SCPI get- and set-messages. For example, if `msg='voltage'`, the
        get-message is `'voltage?'` and the set-message becomes `'voltage {}'`, where `{}` gets
        filled in by the value being set.
    convert : function or callable
        Function that converts both the string returned by querying the instrument and the set-value
        before it is passed to `str.format()`. Usually something like `int` or `float`.
    readonly : bool, optional
        Whether the Facet should be read-only.
    **kwds :
        Any other keywords are passed along to the `Facet` constructor
    """
    get_msg = msg + '?'
    set_msg = None if readonly else msg + ' {}'
    return MessageFacet(get_msg, set_msg, convert=convert, **kwds)
