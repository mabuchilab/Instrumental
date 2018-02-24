# -*- coding: utf-8 -*-
# Copyright 2016-2018 Christopher Rogers, Dodd Gray, and Nate Bogdanowicz
"""
Driver for controlling Thorlabs Kinesis devices.
"""
from __future__ import division

from importlib import import_module

from ...log import get_logger
from ...util import to_str
from .. import ParamSet

from ._kinesis_tli_midlib import NiceTLI

log = get_logger(__name__)

__all__ = []


# Lazily load required device-specific modules
def list_instruments():
    NiceTLI.BuildDeviceList()
    serial_nums = to_str(NiceTLI.GetDeviceListExt()).strip(',').split(',')
    return [ParamSet(cls, serial=serial) for cls,serial in
            ((_try_get_class(sn), sn) for sn in serial_nums)
            if cls]


def _try_get_class(serial):
    try:
        return _get_class(serial)
    except Exception as e:
        log.info(str(e))
        return None


def _get_class(serial):
    """Get a device's Instrument subclass by serial number"""
    type_id = NiceTLI.GetDeviceInfo(serial).typeID
    try:
        return DEVICE_CLASS_CACHE[type_id]
    except KeyError:
        pass

    dev_lib, inst_classname = DEVICE_CLASSES.get(type_id)
    module_name = '._kinesis_{}'.format(dev_lib)
    log.info('Importing %s...', module_name)
    dev_module = import_module(module_name, __package__)
    dev_class = DEVICE_CLASS_CACHE[type_id] = getattr(dev_module, inst_classname)
    return dev_class


# IDs can be found in "Device Serial Number prefix" section of Thorlabs.MotionControl.C_API docs
DEVICE_CLASSES = {
    37: ('ff', 'FilterFlipper'),
    55: ('isc', 'K10CR1'),
}

DEVICE_CLASS_CACHE = {}
