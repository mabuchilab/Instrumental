from instrumental import u


def dim_matches(q1, q2):
    return q1.dimensionality == q2.dimensionality


class TestNIDAQ(object):
    def test_AI_read(self, inst):
        val = inst.ai0.read()
        assert dim_matches(val, u.V)

    def test_AI_read_array(self, inst):
        ai = inst.ai0
        data = ai.read(n_samples=10, fsamp='1kHz')
        assert data[ai.path].shape == (10,)
        assert data['t'].shape == (10,)
        assert dim_matches(data[ai.path], u.V)
        assert dim_matches(data['t'], u.s)
