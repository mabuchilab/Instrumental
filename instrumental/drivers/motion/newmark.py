# -*- coding: utf-8 -*-
"""
Drive for controlling Newmark rotation stages
"""

from . import Motion
from .. import ParamSet
from ...log import get_logger
from .. import VisaMixin
from ..util import check_units
from ... import u
import visa

log = get_logger(__name__)

__all__ = ['NSCA1']


# TODO: There should be a function wrapper
class ImplicitUnitsException(Exception):
    pass


class NSCA1(Motion):
    """ Class for controlling Newmark NSC AI.

    """
    _INST_PARAMS_ = ['serial']

    def _initialize(self):
        self.serial = self._paramset['serial']
        # I only ever use channel 1, but maybe there are needs for more.
        self.channel = 1
        self._rsrc = visa.ResourceManager().open_resource(
            self.serial,
            read_termination='\r',
            write_termination='\r')

    def _cmd(self, cmd):
        self._rsrc.write('@%02d%s' % (self.channel, cmd))
        ret = self._rsrc.read()
        return ret

    def close(self):
        self._rsrc.close()

    @check_units(val='deg')
    def _get_ticks(self, val):
        if val.u not in [u.rad, u.deg]:
            raise ImplicitUnitsException('Mark as degrees or radians')
        return val.to('deg').m * 1e4

    @property
    def angle(self):
        angle = float(self._cmd('PX'))/1e4
        return angle * u.deg

    @angle.setter
    @check_units(angle='deg')
    def angle(self, angle):
        if angle.u not in [u.rad, u.deg]:
            raise ImplicitUnitsException('Mark as degrees or radians')
        self._cmd('ABS')
        self._cmd('X%i' % self._get_ticks(angle))
        self.wait_until_motor_is_idle()

    @check_units(angle='deg')
    def cw(self, angle, background=False):
        """
        Rotate clockwise through a specified angle

        Args:
            angle (Quantity): The amount to rotate
            background (bool, optional): If true, the rotation will occur in
                the background to allow other commands to happen while the
                stage rotates
        """
        if angle.u not in [u.rad, u.deg]:
            raise ImplicitUnitsException('Mark as degrees or radians')
        val = self._get_ticks(angle)
        #if not self._is_safe(self.x + val):
        #    return

        self._cmd('INC')
        self._cmd('X{}'.format(val))

        if background:
            self.wait_until_motor_is_idle()

    @check_units(angle='deg')
    def ccw(self, angle, background=False):
        """
        Rotate counter-clockwise through a specified angle

        Args:
            angle (Quantity): The amount to rotate
            background (bool, optional): If true, the rotation will occur in
                the background to allow other commands to happen while the
                stage rotates
        """
        self.cw(-angle, background)

    def wait_until_motor_is_idle(self):
        try:
            while self.is_moving():
                pass
        except KeyboardInterrupt:
            self._cmd('STOP')
            raise KeyboardInterrupt

    def is_stationary(self):
        return int(self._cmd('MST')) == 0

    def is_moving(self):
        return not self.is_stationary()

    @property
    def velocity(self):
        return int(self._cmd('HSPD')) / 1e4 * u.deg / u.s

    @velocity.setter
    @check_units(velocity='deg/s')
    def velocity(self, velocity):
        ticks_per_second = self._get_ticks((velocity * u.s).to('deg'))
        self._cmd('HSPD=%i' % (ticks_per_second))
