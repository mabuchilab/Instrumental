# -*- coding: utf-8 -*-
"""
Created the 03/03/2022

@author: Sebastien Weber
"""
from __future__ import division

from instrumental import u, Q_
from instrumental.log import get_logger
from instrumental.drivers import Facet
from instrumental.drivers import ParamSet
from instrumental.drivers.motion._madcitylabs.nanodrive_midlib import NiceNanodrive, NiceNanoDriveError
from instrumental.drivers.motion import Motion
from instrumental.drivers.util import check_units

log = get_logger(__name__)


def list_instruments():
    NiceNanodrive.GrabAllHandles()
    handles, Nhandles = NiceNanodrive.GetAllHandles()
    serials = []
    for ind in range(Nhandles):
        serials.append(NiceNanodrive.GetSerialNumber(handles[ind]))
    NiceNanodrive.ReleaseAllHandles()

    pset = []
    for serial in serials:
       pset.append(ParamSet(NanoDrive,  serial=serial, units='µm'))

    return pset


class NanoDriveError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NanoDrive(Motion):
    """
    Class controlling motion devices from MadCityLabs using their Nanodrive  library  Madlib.dll
    """
    _INST_PARAMS_ = ['serial']
    axis_indexes = [1, 2, 3]
    axis_range = dict([])
    _units = ''

    def _initialize(self):
        """
        """
        self.serial = self._paramset['serial']
        self._units = self._paramset['units']
        self._open(self.serial)

    def _open(self, serial):
        """
        Grab all madcitylabs devices connected to the computer and init the one with the given serial number
        Parameters
        ----------
        serial: (int) the device serial number
        """
        NiceNanodrive.ReleaseAllHandles()
        NiceNanodrive.GrabAllHandles()
        self._actuator = NiceNanodrive.Device(serial)

        invalid_axis = []
        for axis_ind in self.axis_indexes:
            axis_range = self.check_axis_range(axis_ind)
            if axis_range is None:
                invalid_axis.append(axis_ind)

        for axis_ind in invalid_axis:
            self.axis_indexes.pop(self.axis_indexes.index(axis_ind))

    def check_axis_range(self, axis_index: int):
        """
        Get range of the given axis and store it in the axis_range parameter
        Parameters
        ----------
        axis_index: (int) the axis id (1: X, 2: Y, 3: Z)
        """
        self.check_axis_error(axis_index)
        try:
            axis_range = self._actuator.GetCalibration(axis_index)
            self.axis_range[axis_index] = Q_(axis_range, self._units)
            return self.axis_range[axis_index]
        except:
            pass

    def check_axis_error(self, axis_index):
        if axis_index not in self.axis_indexes:
            raise NanoDriveError(f'The axis index {axis_index} is invalid and should be within {self.axis_indexes}')

    def close(self):
        NiceNanodrive.ReleaseAllHandles()

    def check_position(self, axis_index: int):
        """
        Ask the device controller for the current position of a given axis in µm
        Parameters
        ----------
        axis_index: (int) the index of the axis

        Returns
        -------
        Quantity: Position of the given axis in µm
        """
        self.check_axis_error(axis_index)
        return Q_(self._actuator.SingleReadN(axis_index), self._units)

    @check_units(target_position='µm')
    def move(self, axis_index=1, target_position=Q_('0µm')):
        """
        Move the given axis to the desired position. The target position is scaled in µm before sent to the controller
        Parameters
        ----------
        axis_index: (int) the index of the axis
        position: (Quantity) with units of length
        """
        self.check_axis_error(axis_index)
        self._actuator.SingleWriteN(target_position.m_as(self._units), axis_index)


if __name__ == '__main__':
    from instrumental import instrument
    paramsets = list_instruments()
    device = NanoDrive(paramsets[0])

    print(f'The position of axis X is {device.check_position(1)}')
    print(f'The position of axis Y is {device.check_position(2)}')

    device.move(1, Q_('12.5µm'))
    device.move(2, Q_(28000, 'nm'))

    print(f'The position of axis X is {device.check_position(1)}')
    print(f'The position of axis Y is {device.check_position(2)}')

    device.close()



