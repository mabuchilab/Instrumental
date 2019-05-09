# Auto-generated 2019-05-06T16:23:11.970004
from collections import OrderedDict

driver_info = OrderedDict([
    ('cameras.pixelfly', {
        'params': ['number'],
        'classes': ['Pixelfly'],
        'imports': ['nicelib', 'win32event'],
    }),
    ('cameras.tsi', {
        'params': ['number', 'serial'],
        'classes': ['TSI_Camera'],
        'imports': ['cffi'],
    }),
    ('cameras.uc480', {
        'params': ['id', 'model', 'serial'],
        'classes': ['UC480_Camera'],
        'imports': ['nicelib >= 0.5', 'pywin32'],
    }),
    ('daq.ni', {
        'params': ['model', 'name', 'serial'],
        'classes': ['NIDAQ'],
        'imports': ['nicelib >= 0.5'],
    }),
    ('funcgenerators.agilent', {
        'params': ['visa_address'],
        'classes': ['Agilent33250A', 'AgilentE4400B', 'AgilentMXG'],
        'imports': [],
        'visa_info': {
            'Agilent33250A': ('Agilent Technologies', ['33250A']),
            'AgilentE4400B': ('Hewlett-Packard', ['ESG-1000B']),
            'AgilentMXG': ('Agilent Technologies', ['N5181A']),
        },
    }),
    ('funcgenerators.rigol', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {
            'DG800': ('Rigol Technologies', ['DG812']),
        },
    }),
    ('funcgenerators.tektronix', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {
            'AFG_3000': ('TEKTRONIX', ['AFG3011', 'AFG3021B', 'AFG3022B', 'AFG3101', 'AFG3102', 'AFG3251', 'AFG3252']),
        },
    }),
    ('laserdiodecontrollers.ilx_lightwave', {
        'params': ['visa_address'],
        'classes': ['LDC3724B'],
        'imports': [],
        'visa_info': {
            'LDC3724B': ('ILX Lightwave', ['3724B']),
        },
    }),
    ('lockins.sr844', {
        'params': ['visa_address'],
        'classes': [],
        'imports': ['visa'],
        'visa_info': {
            'SR844': ('Stanford_Research_Systems', ['SR844']),
        },
    }),
    ('lockins.sr850', {
        'params': ['visa_address'],
        'classes': [],
        'imports': ['visa'],
        'visa_info': {
            'SR850': ('Stanford_Research_Systems', ['SR850']),
        },
    }),
    ('motion._kinesis.ff', {
        'params': ['serial'],
        'classes': ['FilterFlipper'],
        'imports': ['nicelib'],
    }),
    ('motion._kinesis.isc', {
        'params': ['serial'],
        'classes': ['K10CR1'],
        'imports': ['nicelib'],
    }),
    ('motion.apt', {
        'params': ['serial'],
        'classes': ['TDC001_APT'],
        'imports': ['serial'],
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
    ('motion.newmark', {
        'params': ['serial'],
        'classes': ['NSCA1'],
        'imports': ['visa'],
    }),
    ('motion.tdc_001', {
        'params': ['serial'],
        'classes': ['TDC001'],
        'imports': ['cffi', 'nicelib'],
    }),
    ('multimeters.hp', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {
            'HPMultimeter': ('HEWLETT-PACKARD', ['34401A']),
        },
    }),
    ('powermeters.thorlabs', {
        'params': ['visa_address'],
        'classes': ['PM100D'],
        'imports': [],
        'visa_info': {
            'PM100D': ('Thorlabs', ['PM100D']),
        },
    }),
    ('powersupplies.gw_instek', {
        'params': ['visa_address'],
        'classes': ['GPD_3303S'],
        'imports': [],
        'visa_info': {
            'GPD_3303S': ('GW INSTEK', ['GPD-3303S']),
        },
    }),
    ('scopes.agilent', {
        'params': ['visa_address'],
        'classes': ['DSO_1000'],
        'imports': ['pyvisa', 'visa'],
        'visa_info': {
            'DSO_1000': ('Agilent Technologies', ['DSO1024A']),
        },
    }),
    ('scopes.tektronix', {
        'params': ['visa_address'],
        'classes': ['MSO_DPO_2000', 'MSO_DPO_4000', 'TDS_1000', 'TDS_200', 'TDS_2000', 'TDS_3000'],
        'imports': ['pyvisa', 'visa'],
        'visa_info': {
            'MSO_DPO_2000': ('TEKTRONIX', ['MSO2012', 'MSO2014', 'MSO2024', 'DPO2012', 'DPO2014', 'DPO2024']),
            'MSO_DPO_4000': ('TEKTRONIX', ['MSO4032', 'DPO4032', 'MSO4034', 'DPO4034', 'MSO4054', 'DPO4054', 'MSO4104', 'DPO4104']),
            'TDS_1000': ('TEKTRONIX', ['TDS 1001B', 'TDS 1002B', 'TDS 1012B']),
            'TDS_200': ('TEKTRONIX', ['TDS 210', 'TDS 220', 'TDS 224']),
            'TDS_2000': ('TEKTRONIX', ['TDS 2002B', 'TDS 2004B', 'TDS 2012B', 'TDS 2014B', 'TDS 2022B', 'TDS 2024B']),
            'TDS_3000': ('TEKTRONIX', ['TDS 3012', 'TDS 3012B', 'TDS 3012C', 'TDS 3014', 'TDS 3014B', 'TDS 3014C', 'TDS 3032', 'TDS 3032B', 'TDS 3032C', 'TDS 3034', 'TDS 3034B', 'TDS 3034C', 'TDS 3052', 'TDS 3052B', 'TDS 3052C', 'TDS 3054', 'TDS 3054B', 'TDS 3054C']),
        },
    }),
    ('spectrometers.bristol', {
        'params': ['port'],
        'classes': ['Bristol_721'],
        'imports': [],
    }),
    ('spectrometers.thorlabs_ccs', {
        'params': ['model', 'serial', 'usb'],
        'classes': ['CCS'],
        'imports': ['cffi', 'nicelib', 'visa'],
    }),
    ('spectrumanalyzers.rohde_schwarz', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {},
    }),
    ('tempcontrollers.covesion', {
        'params': ['visa_address'],
        'classes': ['CovesionOC'],
        'imports': ['pyvisa'],
        'visa_info': {},
    }),
    ('tempcontrollers.hcphotonics', {
        'params': ['visa_address'],
        'classes': ['TC038'],
        'imports': ['pyvisa'],
        'visa_info': {},
    }),
    ('lasers.femto_ferb', {
        'params': ['visa_address'],
        'classes': [],
        'imports': [],
        'visa_info': {},
    }),
    ('powermeters.newport', {
        'params': ['visa_address'],
        'classes': ['Newport_1830_C'],
        'imports': [],
        'visa_info': {},
    }),
    ('cameras.pco', {
        'params': ['interface', 'number'],
        'classes': ['PCO_Camera'],
        'imports': ['cffi', 'nicelib', 'pycparser'],
    }),
    ('vacuum.sentorr_mod', {
        'params': ['port'],
        'classes': ['SenTorrMod'],
        'imports': ['serial'],
    }),
    ('wavemeters.burleigh', {
        'params': ['visa_address'],
        'classes': ['WA_1000'],
        'imports': [],
        'visa_info': {},
    }),
])
