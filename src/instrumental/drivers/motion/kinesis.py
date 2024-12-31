# -*- coding: utf-8 -*-
# Copyright 2016-2020 Christopher Rogers, Dodd Gray, and Nate Bogdanowicz
"""
Driver for controlling Thorlabs Kinesis devices.
"""
from __future__ import division

import atexit
from importlib import import_module

from ...log import get_logger
from ...util import to_str
from .. import ParamSet

from ._kinesis.tli_midlib import NiceTLI

log = get_logger(__name__)

__all__ = []


# Lazily load required device-specific modules
def list_instruments():
    NiceTLI.BuildDeviceList()
    serial_nums = to_str(NiceTLI.GetDeviceListExt()).strip(',').split(',')
    return [ParamSet(cls, serial=serial) for cls,serial in
            ((_try_get_class(sn), sn) for sn in serial_nums)
            if cls]


def initialize_simulations():
    """Initialize a connection to the Simulation Manager, which must already be running.

    Can be called multiple times. For a simulated device to show up in `list_instruments`, this
    function must be called after the device's creation.

    This function automatically registers ``uninitialize_simulations`` to be called upon program
    exit.
    """
    NiceTLI.InitializeSimulations()
    atexit.register(uninitialize_simulations)


def uninitialize_simulations():
    """Release the connection to the Simulation Manager.

    This function is automatically registered by ``initialize_simulations`` to be called upon
    program exit.
    """
    NiceTLI.UninitializeSimulations()


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
    module_name = '._kinesis.{}'.format(dev_lib)
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
