from __future__ import division

from instrumental import u, Q_
from instrumental.log import get_logger
from instrumental.drivers import Facet
from instrumental.drivers import ParamSet
from instrumental.drivers.motion.smaract import SmaractDevice
from instrumental.drivers.motion._smaract.scu_midlib import NiceSCU, SmarActError, OPERATING_MODES
from instrumental.drivers.util import check_units

log = get_logger(__name__)


def list_instruments():
    ids, Nids = NiceSCU.GetAvailableDevices(2048)
    if Nids == 1:
        ids = [ids]
    NiceSCU.InitDevices(OPERATING_MODES['SA_SYNCHRONOUS_COMMUNICATION'])
    pset = []
    for ind, idd in enumerate(ids):
        try:
            rotation = False
            ind_channel = 0
            while True:
                act = NiceSCU.Actuator(ind, ind_channel)
                try:
                    act.GetStatus_S()
                except SmarActError as e:
                    # will fire an error if the ind_channel is invalid
                    break
                try:
                    sensor = bool(act.GetSensorPresent_S())
                except SmarActError as e:
                    sensor = False
                if sensor:
                    try:
                        act.GetAngle_S()
                        rotation = True
                    except SmarActError:
                        rotation = False
                ind_channel += 1
        except SmarActError as e:
            pass
        for ind_channel in range(ind_channel):
            pset.append(ParamSet(SCU if not sensor else SCURotation if rotation else SCULinear,
                                 id=idd, index=ind_channel, sensor=sensor,
                                 rotation=rotation, nchannels=ind_channel+1,
                                 units='steps' if not sensor else 'deg' if rotation else 'µm'))
    NiceSCU.ReleaseDevices()

    return pset


FREQ_LIMITS = Q_((1, 18500), units='Hz')  # Hz
AMP_LIMITS = Q_((15, 100), units='V')  # V


class SCU(SmaractDevice):
    """ Class for controlling actuators from smaract using the SCU controller

    Takes the device index and channel index as init parameters

    """
    _INST_PARAMS_ = ['id', 'index']
    dev_type = 'stepper'
    units = 'steps'

    def _initialize(self):
        """

        Returns
        -------

        """
        self.device_id = self._paramset['id']
        self.channel_index = self._paramset['index']
        self.nchannels = self._paramset['nchannels']
        self._hold_time = 0
        self._actuator = None
        self._internal_counter = 0
        self._frequency = 100
        self._open(self.device_id)

    def _open(self, device_id):
        try:
            NiceSCU.ReleaseDevices()
        except SmarActError as e:
            log.info('Cannot release SCU controller devices as none have been initialized yet')

        NiceSCU.AddDeviceToInitDevicesList(device_id)
        NiceSCU.InitDevices(OPERATING_MODES['SA_SYNCHRONOUS_COMMUNICATION'])

        self._actuator = NiceSCU.Actuator(0, self.channel_index)

    def close(self):
        NiceSCU.ReleaseDevices()

    def stop(self):
        self._actuator.Stop_S()

    @classmethod
    def get_devices(cls):
        devs, Ndevs = NiceSCU.GetAvailableDevices(2048)
        if Ndevs == 1:
            return [devs]
        else:
            return devs

    def has_sensor(self):
        ret = self._actuator.GetSensorPresent_S()
        if ret == NiceSCU._defs['SA_SENSOR_PRESENT']:
            return True
        else:
            return False

    @Facet(units='ms')
    def hold_time(self):
        return self._hold_time

    @hold_time.setter
    def hold_time(self, time):
        self._hold_time = time

    @Facet
    def is_referenced(self):
        ret = self._actuator.GetPhysicalPositionKnown_S()
        if ret == NiceSCU._defs['SA_PHYSICAL_POSITION_KNOWN.']:
            return True
        else:
            return False

    @Facet(units='V', limits=AMP_LIMITS.m_as('V'))
    def amplitude(self):

        return self._actuator.GetAmplitude_S() / 10

    @property
    def amplitude_limits(self):
        return AMP_LIMITS

    @amplitude.setter
    def amplitude(self, amp):
        self._internal_counter = 0  # reset the internal counter as it has no meaning if amplitude change
        self._actuator.SetAmplitude_S(int(amp * 10))

    @Facet(units='Hz', limits=FREQ_LIMITS.m_as('Hz'))
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, freq):
        self._frequency = freq

    @property
    def frequency_limits(self):
        return FREQ_LIMITS

    def move_to(self, value, move_type='rel'):
        """

        Parameters
        ----------
        value: (float) position in steps
        move_type: (str) without sensor can only be 'rel' for relative motion fro a given number of steps
        """
        if isinstance(value, Q_):
            value = value.magnitude

        if move_type == 'abs':
            log.info('No Absolute Move possible, only relative stepping is available using a relative move using'
                     'internal counter')
            rel_value = value-self._internal_counter
            self._actuator.MoveStep_S(int(rel_value), int(self.amplitude.magnitude * 10),
                                      int(self.frequency.magnitude))
            self._internal_counter += rel_value
        else:
            self._actuator.MoveStep_S(int(value), int(self.amplitude.magnitude * 10),
                                      int(self.frequency.magnitude))
            self._internal_counter += value

    def move_home(self, autozero=True):
        if not self.has_sensor:

            log.info('No possible homing as no sensor is present, trying to go to 0 internal counter')
            self.move_to(Q_(-self._internal_counter, ''), 'rel')

        else:
            self._actuator.MoveToReference_S(self.hold_time.magnitude,
                                           NiceSCU._defs['SA_AUTO_ZERO'] if autozero else
                                           NiceSCU._defs['SA_NO_AUTO_ZERO'])

    def check_position(self):
        return Q_(self._internal_counter, '')


class SCULinear(SCU):
    _INST_PARAMS_ = ['id', 'index']
    dev_type = 'linear'
    units = 'µm'

    @check_units(value='µm')
    def move_to(self, value, move_type='abs'):
        """

        Parameters
        ----------
        value: (float) position in µm
        move_type: (str) either 'rel' for relative motion or 'abs' for absolute positioning
        """

        if move_type == 'abs':
            self._actuator.MovePositionAbsolute_S(value.m_as('µm') * 10, self.hold_time.magnitude)  # takes value in 1/10 of µm
        else:
            self._actuator.MovePositionRelative_S(value.m_as('µm') * 10, self.hold_time.magnitude)   # takes value in 1/10 of µm

    def check_position(self):
        return Q_(0.1 * self._actuator.GetPosition_S(), 'µm')


class SCURotation(SCU):
    _INST_PARAMS_ = ['id', 'index']
    dev_type = 'rotation'
    units = 'deg'

    @check_units(value='deg')
    def move_to(self, value, move_type='abs'):
        """

        Parameters
        ----------
        value: (float) rotation in deg
        move_type: (str) either 'rel' for relative motion or 'abs' for absolute positioning
        """

        if move_type == 'abs':
            self._actuator.MoveAngleAbsolute_S(value.m_as('mdeg') * 10, self.hold_time.magnitude)  # takes value in 1/10 of µm
        else:
            self._actuator.MoveAngleRelative_S(value.m_as('mdeg') * 10, self.hold_time.magnitude)  # takes value in 1/10 of µm

    def check_position(self):
        return Q_(self._actuator.GetAngle_S(), 'deg')


if __name__ == '__main__':
    from instrumental import instrument
    paramsets = list_instruments()
    # inst = instrument(paramsets[0])
    # try:
    #     NiceSCU.ReleaseDevices()
    # except SmarActError as e:
    #     print(e)
    ids = SCU.get_devices()
    dev = instrument(paramsets[0])
    dev.move_home()
    pos = dev.check_position()
    pass
    dev.close()

