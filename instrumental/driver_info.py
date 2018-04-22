# Auto-generated 2017-11-21T15:44:02.583501
from collections import OrderedDict

driver_info = OrderedDict([
    ('cameras.picam', {
        'params': [],
        'classes': [],
        'imports': ['nicelib'],
    }),
    ('cameras.pixelfly', {
        'params': ['number'],
        'classes': ['Pixelfly'],
        'imports': ['win32event', 'nicelib'],
    }),
    ('cameras.pvcam', {
        'params': [],
        'classes': [],
        'imports': ['cffi'],
    }),
    ('cameras.tsi', {
        'params': ['serial', 'number'],
        'classes': ['TSI_Camera'],
        'imports': ['cffi'],
    }),
    ('cameras.uc480', {
        'params': ['serial', 'id', 'model'],
        'classes': ['UC480_Camera'],
        'imports': ['win32event', 'nicelib'],
    }),
    ('daq.ni', {
        'params': ['name', 'serial', 'model'],
        'classes': ['NIDAQ'],
        'imports': ['nicelib'],
    }),
    ('funcgenerators.tektronix', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {'AFG_3000': ('TEKTRONIX', ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102', 'AFG3251', 'AFG3252'])},
    }),
    ('lockins.sr850', {
        'params': ['visa_address'],
        'classes': [],
        'imports': ['visa'],
        'visa_info': {'SR850': ('Stanford_Research_Systems', ['SR850'])},
    }),
    ('motion.USMC', {
        'params': [],
        'classes': ['USMC'],
        'imports': ['nicelib'],
    }),
    ('motion.ecc100', {
        'params': ['id'],
        'classes': ['ECC100'],
        'imports': [],
    }),
    ('motion.filter_flipper', {
        'params': ['serial'],
        'classes': ['Filter_Flipper'],
        'imports': ['cffi', 'nicelib'],
    }),
    ('motion.kinesis', {
        'params': ['serial'],
        'classes': ['K10CR1'],
        'imports': ['nicelib'],
    }),
    ('motion.tdc_001', {
        'params': ['serial'],
        'classes': ['TDC001'],
        'imports': ['nicelib', 'cffi'],
    }),
    ('motion.~_build_USMC', {
        'params': [],
        'classes': [],
        'imports': ['nicelib'],
    }),
    ('multimeters.hp', {
        'params': ['visa_address'],
        'classes': ['HP3478A','HP34000'],
        'imports': [],
        'visa_info': {'HP34000': ('HEWLETT-PACKARD', ['34401A']),'HP3478A': ('HEWLETT-PACKARD', ['3478A'])}
    }),
    ('powermeters.thorlabs', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {'PM100D': ('Thorlabs', ['PM100D'])},
    }),
    ('rfspectrumanalyzers.hp', {
        'params': ['visa_address'],
        'classes': ['HP4395'],
        'imports': ['visa','pyvisa'],
        'visa_info': {'HP4395': ('HEWLETT-PACKARD', ['4395A'])},
    }),
    ('scopes.tektronix', {
        'params': ['visa_address'],
        'classes': [],
        'imports': ['visa', 'pyvisa'],
        'visa_info': {'TDS_200': ('TEKTRONIX', ['TDS 210']), 'TDS_3000': ('TEKTRONIX', ['TDS 3032', 'TDS 3034B']), 'MSO_DPO_4000': ('TEKTRONIX', ['MSO4034', 'DPO4034', 'DPO2024'])},
    }),
    ('spectrometers.bristol', {
        'params': ['port'],
        'classes': ['Bristol_721'],
        'imports': [],
    }),
    ('spectrometers.thorlabs_ccs', {
        'params': ['serial', 'usb', 'model'],
        'classes': ['CCS'],
        'imports': ['visa', 'cffi', 'nicelib'],
    }),
    ('spectrometers.hp', {
        'params': ['visa_address'],
        'classes': ['HPOSA'],
        'imports': ['visa','pyvisa'],
        'visa_info': {'HPOSA': ('HEWLETT-PACKARD', ['70951B'])},
    }),
    ('spectrometers.ando', {
        'params': ['visa_address'],
        'classes': ['AQ6331'],
        'imports': ['visa','pyvisa'],
        'visa_info': {'AQ6331': ('ANDO', ['AQ6331'])},
    }),
    ('tempcontrollers.covesion', {
        'params': ['OC_visa_address','version'],
        'classes': ['OC'],
        'imports': ['pyvisa'],
    }),
    ('tempcontrollers.hcphotonics', {
        'params': [],
        'classes': [],
        'imports': ['pyvisa'],
    }),
    ('lasers.femto_ferb', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': None,
    }),
    ('powermeters.newport', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': None,
    }),
    ('cameras.pco', {
        'params': ['number', 'interface'],
        'classes': ['PCO_Camera'],
        'imports': ['cffi', 'pycparser', 'nicelib'],
    }),
    ('vacuum.sentorr_mod', {
        'params': ['port'],
        'classes': ['SenTorrMod'],
        'imports': ['serial'],
    }),
    ('wavemeters.burleigh', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': None,
    }),
])
