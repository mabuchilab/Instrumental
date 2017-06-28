# Auto-generated 2017-06-27T19:35:13.494000
from collections import OrderedDict


driver_params = OrderedDict([
    (('cameras', 'tsi'), ['serial', 'number']),
    (('powermeters', 'thorlabs'), ['visa_address']),
])

driver_imports = OrderedDict([
    ('cameras.pco', ['cffi', 'pycparser', 'nicelib']),
    ('cameras.pixelfly', ['win32event', 'nicelib']),
    ('cameras.pvcam', ['cffi']),
    ('cameras.tsi', ['cffi']),
    ('cameras.uc480', ['win32event', 'nicelib']),
    ('daq.ni', ['nicelib']),
    ('funcgenerators.tektronix', ['instrumental']),
    ('lasers.femto_ferb', ['visa']),
    ('lockins.sr850', ['visa']),
    ('motion.ecc100', []),
    ('motion.filter_flipper', ['cffi', 'nicelib']),
    ('motion.kinesis', ['nicelib']),
    ('motion.tdc_001', ['nicelib', 'cffi']),
    ('multimeters.hp', ['instrumental']),
    ('powermeters.newport', []),
    ('powermeters.thorlabs', []),
    ('scopes.tektronix', ['visa', 'instrumental']),
    ('spectrometers.bristol', []),
    ('spectrometers.thorlabs_ccs', ['visa', 'cffi', 'nicelib']),
    ('vacuum.sentorr_mod', ['serial']),
    ('wavemeters.burleigh', []),
])
