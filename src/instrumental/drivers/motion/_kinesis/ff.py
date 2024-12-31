# -*- coding: utf-8 -*-
# Copyright 2018 Nate Bogdanowicz
from __future__ import division

from time import sleep
from enum import Enum

from .... import Q_
from ...util import check_units, check_enums
from .. import Motion
from .ff_midlib import NiceFF
import nicelib  # noqa (nicelib dep is hidden behind import of ff_midlib)


class Position(Enum):
    """ The position of the flipper. """
    one = 1
    two = 2
    moving = 0


class FilterFlipper(Motion):
    """ Driver for controlling Thorlabs Filter Flippers

    The polling period, which is how often the device updates its status, is
    passed as a pint quantity with units of time and is optional argument,
    with a default of 200ms
    """
    _INST_PARAMS_ = ['serial']

    @check_units(polling_period='ms')
    def _initialize(self, polling_period='200ms'):
        self.serial = self._paramset['serial']
        self._dev = NiceFF.Flipper(self.serial)

        self._open()
        self._dev.LoadSettings()
        self._start_polling(polling_period)

    def _open(self):
        return self._dev.Open()

    def close(self):
        return self._dev.Close()

    @check_units(polling_period='ms')
    def _start_polling(self, polling_period='200ms'):
        """Starts polling to periodically update the device status.

        Parameters
        ----------
        polling_period: pint quantity with units of time """
        self.polling_period = polling_period.to('ms').magnitude
        return self._dev.StartPolling(self.polling_period)

    def get_position(self):
        """ Get the position of the flipper.

        Returns an instance of Position.
        Note that this represents the position at the most recent polling
        event."""
        position = self._dev.GetPosition()
        return Position(position)

    def flip(self):
        """ Flips the position of the filter.  """
        position = self.get_position()
        if position == Position.one:
            return self.move_to(Position.two)
        elif position == Position.two:
            return self.move_to(Position.one)
        else:
            raise Exception("Could not flip because the current position is not valid")

    @check_enums(position=Position)
    def move_to(self, position):
        """ Moves the flipper to the indicated position.

        Returns immediatley.

        Parameters
        ----------
        position: instance of Position
            should not be 'Position.moving' """
        if not self.isValidPosition(position):
            raise ValueError("Not a valid position")
        position = position.value
        return self._dev.MoveToPosition(position)

    @check_units(delay='ms')
    @check_enums(position=Position)
    def move_and_wait(self, position, delay='100ms'):
        """ Moves to the indicated position and waits until that position is
        reached.

        Parameters
        ----------
        position: instance of Position
            should not be 'Position.moving'
        delay: pint quantity with units of time
            the period with which the position of the flipper is checked."""
        current_position = self.get_position()
        if not self.isValidPosition(position):
            raise ValueError("Not a valid position")
        if current_position != position:
            transit_time = self.get_transit_time()
            self.move_to(position)
            sleep(transit_time.to('s').magnitude)
            while self.get_position() != position:
                sleep(delay.to('s').magnitude)

    @check_enums(position=Position)
    def isValidPosition(self, position):
        """ Indicates if it is possible to move to the given position.

        Parameters
        ----------
        position: instance of Position """
        ismoving = position == Position.moving
        isposition = isinstance(position, Position)
        if ismoving or not isposition:
            return False
        else:
            return True

    def home(self):
        """ Homes the device """
        return self._dev.Home()

    def get_transit_time(self):
        """ Returns the transit time.

        The transit time is the time to transition from
        one filter position to the next."""
        transit_time = self._dev.GetTransitTime()
        return Q_(transit_time, 'ms')

    @check_units(transit_time='ms')
    def set_transit_time(self, transit_time='500ms'):
        """ Sets the transit time.
        The transit time is the time to transition from
        one filter position to the next.

        Parameters
        ----------
        transit_time: pint quantity with units of time """
        transit_time = transit_time.to('ms').magnitude
        return int(self._dev.SetTransitTime(transit_time))
