from instrumental import plotting as p
from matplotlib import pyplot as plt
from numpy import sin, pi, arange

def curve(x, amp, freq, phase):
    return amp * sin(2*pi*freq*x + phase)

params = {
    'freq': 3,
    'amp': {
        'min':-10,
        'max':10,
        'init':5
    },
    'phase': {
        'min':0,
        'max':2*pi,
        'init':pi
    }
}

t = arange(0.0, 1.0, 0.001)
p.param_plot(t, curve, params)
plt.gca().plot(t, t)
plt.xlabel("X Label")
plt.ylabel("Y Label")
plt.title("Title")
plt.show()
