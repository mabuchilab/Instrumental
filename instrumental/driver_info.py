# Auto-generated 2018-02-20T01:27:08.936616
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
        'imports': ['pywin32', 'nicelib >= 0.5'],
    }),
    ('daq.ni', {
        'params': ['model', 'serial', 'name'],
        'classes': ['NIDAQ'],
        'imports': ['nicelib >= 0.5'],
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
    ('multimeters.hp', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {'HPMultimeter': ('HEWLETT-PACKARD', ['34401A'])},
    }),
    ('powermeters.thorlabs', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {'PM100D': ('Thorlabs', ['PM100D'])},
    }),
    ('scopes.tektronix', {
        'params': ['visa_address'],
        'classes': ['TDS_200', 'TDS_1000', 'TDS_2000', 'TDS_3000', 'MSO_DPO_4000'],
        'imports': ['visa', 'pyvisa'],
        'visa_info': {'TDS_200': ('TEKTRONIX', ['TDS 210', 'TDS 220', 'TDS 224']), 'TDS_1000': ('TEKTRONIX', ['TDS 1001B', 'TDS 1002B', 'TDS 1012B']), 'TDS_2000': ('TEKTRONIX', ['TDS 2002B', 'TDS 2004B', 'TDS 2012B', 'TDS 2014B', 'TDS 2022B', 'TDS 2024B']), 'TDS_3000': ('TEKTRONIX', ['TDS 3012', 'TDS 3012B', 'TDS 3012C', 'TDS 3014', 'TDS 3014B', 'TDS 3014C', 'TDS 3032', 'TDS 3032B', 'TDS 3032C', 'TDS 3034', 'TDS 3034B', 'TDS 3034C', 'TDS 3052', 'TDS 3052B', 'TDS 3052C', 'TDS 3054', 'TDS 3054B', 'TDS 3054C']), 'MSO_DPO_4000': ('TEKTRONIX', ['MSO4032', 'DPO4032', 'MSO4034', 'DPO4034', 'MSO4054', 'DPO4054', 'MSO4104', 'DPO4104'])},
    }),
    ('spectrometers.bristol', {
        'params': ['port'],
        'classes': ['Bristol_721'],
        'imports': [],
    }),
    ('spectrometers.thorlabs_ccs', {
        'params': ['model', 'usb', 'serial'],
        'classes': ['CCS'],
        'imports': ['visa', 'cffi', 'nicelib'],
    }),
    ('tempcontrollers.covesion', {
        'params': ['visa_address'],
        'classes': ['CovesionOC'],
        'imports': ['pyvisa'],
        'visa_info': None,
    }),
    ('tempcontrollers.hcphotonics', {
        'params': ['visa_address'],
        'classes': ['TC038'],
        'imports': ['pyvisa'],
        'visa_info': None,
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
        'params': ['interface', 'number'],
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
