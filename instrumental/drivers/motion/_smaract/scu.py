from __future__ import division

from instrumental import u
from instrumental.log import get_logger
from instrumental.drivers import Facet
from instrumental.drivers import ParamSet
from instrumental.drivers.motion import Motion
from instrumental.drivers.motion._smaract.scu_midlib import NiceSCU, SmarActError, OPERATING_MODES


log = get_logger(__name__)

_INST_PARAMS = ['device_id']
_INST_CLASSES = ['SCULinear', 'SCUAngular']


def list_instruments():
    ids, Nids = NiceSCU.GetAvailableDevices(2048)
    if Nids == 1:
        ids = [ids]
    return [ParamSet(id) for id in ids]


class SCU(Motion):
    """ Class for controlling actuators from smaract using the SCU controller

    Takes the device index and channel index as init parameters

    """

    def _initialize(self, device_index=0, channel_index=0):
        """

        Parameters
        ----------
        device_index
        channel_index

        Returns
        -------

        """
        self.device_id = self._paramset['device_id']
        self.device_index = device_index
        self.channel_index = channel_index

        self._open([self.device_id])

        self._dev = NiceSCU.Actuator(self.device_index, self.channel_index)

    def _open(self, ids):
        try:
            NiceSCU.ReleaseDevices()
        except SmarActError as e:
            print(e)

        for id in ids:
            NiceSCU.AddDeviceToInitDevicesList(id)
        NiceSCU.InitDevices()
        self.actuator = NiceSCU.Actuator(self.device_index, self.channel_index)

    def close(self):
        NiceSCU.ReleaseDevices()

    @classmethod
    def get_devices(cls):
        devs, Ndevs = cls._lib.GetAvailableDevices(2048)
        if Ndevs == 1:
            return [devs]
        else:
            return devs


class SCULinear(SCU):
    pass


if __name__ == '__main__':
    paramsets = list_instruments()
    try:
        NiceSCU.ReleaseDevices()
    except SmarActError as e:
        print(e)
    ids = SCU.get_devices()
    scu = SCU(0, 0, ids)

