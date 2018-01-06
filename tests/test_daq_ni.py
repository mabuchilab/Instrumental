from instrumental import instrument, u
daq = instrument(nidaq_devname='Dev1')


def dim_matches(q1, q2):
    return q1.dimensionality == q2.dimensionality


def test_AI_read():
    val = daq.ai0.read()
    assert dim_matches(val, u.V)


def test_AI_read_array():
    ai = daq.ai0
    data = ai.read(n_samples=10, fsamp='1kHz')
    assert data[ai.path].shape == (10,)
    assert data['t'].shape == (10,)
    assert dim_matches(data[ai.path], u.V)
    assert dim_matches(data['t'], u.s)
