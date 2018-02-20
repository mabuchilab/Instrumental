class TestUC480_Camera(object):
    def test_gain(self, inst):
        inst.master_gain = 2.0
        assert inst.master_gain == 2.0
