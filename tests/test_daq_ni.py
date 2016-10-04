from instrumental import instrument, u
daq = instrument(nidaq_devname='Dev1')

def dim_matches(q1, q2):
    return q1.dimensionality == q2.dimensionality

def test_AI_read():
    val = daq.ai0.read()
    assert dim_matches(val, u.V)
