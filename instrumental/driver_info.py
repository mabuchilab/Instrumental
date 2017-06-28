# Auto-generated 2017-06-28T20:41:27.641000
from collections import OrderedDict

driver_info = OrderedDict([
    ('cameras.pco', {
        'params': [],
        'imports': ['cffi', 'pycparser', 'nicelib'],
    }),
    ('cameras.pixelfly', {
        'params': [],
        'imports': ['win32event', 'nicelib'],
    }),
    ('cameras.pvcam', {
        'params': [],
        'imports': ['cffi'],
    }),
    ('cameras.tsi', {
        'params': ['serial', 'number'],
        'imports': ['cffi'],
    }),
    ('cameras.uc480', {
        'params': [],
        'imports': ['win32event', 'nicelib'],
    }),
    ('daq.ni', {
        'params': [],
        'imports': ['nicelib'],
    }),
    ('funcgenerators.tektronix', {
        'params': [],
        'imports': ['instrumental'],
    }),
    ('lasers.femto_ferb', {
        'params': [],
        'imports': ['visa'],
    }),
    ('lockins.sr850', {
        'params': [],
        'imports': ['visa'],
    }),
    ('motion.ecc100', {
        'params': [],
        'imports': [],
    }),
    ('motion.filter_flipper', {
        'params': [],
        'imports': ['cffi', 'nicelib'],
    }),
    ('motion.kinesis', {
        'params': [],
        'imports': ['nicelib'],
    }),
    ('motion.tdc_001', {
        'params': [],
        'imports': ['nicelib', 'cffi'],
    }),
    ('multimeters.hp', {
        'params': [],
        'imports': ['instrumental'],
    }),
    ('powermeters.newport', {
        'params': [],
        'imports': [],
    }),
    ('powermeters.thorlabs', {
        'params': ['visa_address'],
        'imports': [],
        'visa_info': {'PM100D': ('Thorlabs', ['PM100D'])},
    }),
    ('scopes.tektronix', {
        'params': [],
        'imports': ['visa', 'instrumental'],
    }),
    ('spectrometers.bristol', {
        'params': [],
        'imports': [],
    }),
    ('spectrometers.thorlabs_ccs', {
        'params': [],
        'imports': ['visa', 'cffi', 'nicelib'],
    }),
    ('vacuum.sentorr_mod', {
        'params': [],
        'imports': ['serial'],
    }),
    ('wavemeters.burleigh', {
        'params': [],
        'imports': [],
    }),
])
