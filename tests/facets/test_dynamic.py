import pytest
from instrumental.drivers import Instrument, ManualFacet


class MyPowerSupply(Instrument):
    voltage = ManualFacet(units='volts')

    @voltage.limits_getter
    def voltage(self, facet):
        return (0, 12, None)


def test_limits():
    ps = MyPowerSupply()
    ps.voltage = '10 V'

    with pytest.raises(ValueError, match='Value above upper limit'):
        ps.voltage = '13 V'

    with pytest.raises(ValueError, match='Value below lower limit'):
        ps.voltage = '-1 V'
