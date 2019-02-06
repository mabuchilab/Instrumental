import pytest
from pint.errors import DimensionalityError
from instrumental import Q_
from instrumental.drivers import Instrument, ManualFacet


class MyPowerSupply(Instrument):
    voltage = ManualFacet(units='volts')
    current = ManualFacet(units='amps')


def test():
    ps = MyPowerSupply()
    ps.voltage = '12V'
    assert ps.voltage == Q_(12, 'volts')

    with pytest.raises(DimensionalityError):
        ps.voltage = '200 mA'
