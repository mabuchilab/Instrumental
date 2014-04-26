# -*- coding: utf-8 -*-
import os
import os.path
import shutil
from datetime import date, datetime
import numpy as np

from .fitting import guided_trace_fit, guided_ringdown_fit
from . import u, Q_, conf
from .drivers import scopes

# Fix for Python 2
try: input = raw_input
except NameError: pass

prev_data_fname = ''

class DataSession(object):
    def __init__(self, name):
        self.name = name
        self.data_dir = self.find_data_dir()
        self.start_time = datetime.now()
        self.end_time = None
        self.measurement_num = 1
        self.meas_list = {}

    def add_measurement(self, meas_dict, comment=None):
        filename = os.path.join(self.data_dir, "Measurement {}.csv".format(self.measurement_num))
        self.measurement_num += 1
        with open(filename, 'w') as f:
            f.write('# Data saved {}\n\n'.format(datetime.now().isoformat(' ')))
            for name, value in meas_dict.items():

                # Hack for not treating ints as floats
                if np.asarray(value.magnitude).dtype.kind == 'i':
                    fmt = '{}'
                else:
                    fmt = '{:.8e}'

                f.write(('{} = '+fmt+'\n').format(name, value))
                if name not in self.meas_list:
                    self.meas_list[name] = []
                self.meas_list[name].append(value)

    def save_summary(self, comment=None):
        arrays, labels = [], []
        for name, qlist in self.meas_list.items():
            qarr = self._quantity_list_to_array(qlist)
            unit = qarr.units
            labels.append('{} ({})'.format(name, unit))
            arrays.append(qarr.magnitude)

        timestamp = "Data saved {}".format(datetime.now().isoformat(' '))
        labels = ', '.join(labels)
        header = '\n'.join([timestamp, '', labels])

        data = np.array(arrays).T
        filename = os.path.join(self.data_dir, "Summary.csv")
        np.savetxt(filename, data, header=header, delimiter=',')


    def _quantity_list_to_array(self, qlist):
        # I feel like there should already exist a function for this...
        units = qlist[0].units
        mags = np.array([q.to(units).magnitude for q in qlist])
        return Q_(mags, units)


    def find_data_dir(self):
        base_dir = conf.prefs['data_directory']
        date_subdir = date.today().isoformat()
        session_subdir = self.name
        data_dir = os.path.join(base_dir, date_subdir, session_subdir)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir

def _save_data(time, signal, full_filename, comment=''):
    full_dir = os.path.dirname(full_filename)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)
    
    timestamp = "Data saved {}".format(datetime.now().isoformat(' '))
    labels = "Time ({}), Signal ({})".format(time.units, signal.units)
    header = '\n'.join([timestamp, comment, '', labels])
    
    data = np.array((time.magnitude, signal.magnitude)).T
    np.savetxt(full_filename, data, header=header, delimiter=",")


def _save_ringdown(time, signal, full_filename):
    full_dir = os.path.dirname(full_filename)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)
    
    timestamp = "Data saved{}".format(datetime.now().isoformat(' '))
    labels = "Time ({}), Signal ({})".format(time.units, signal.units)
    header = '\n'.join([timestamp, '', labels])
    
    data = np.array((time.magnitude, signal.magnitude)).T
    np.savetxt(full_filename, data, header=header, delimiter=",")


def _save_summary(full_data_filename, FWHM):
    # Save directory must exist
    full_dir, data_fname = os.path.split(full_data_filename)
    summary_fname = os.path.join(full_dir, 'Summary.tsv')
    
    if not os.path.exists(summary_fname):
        summary_file = open(summary_fname, 'w')
        summary_file.write('# FWHM (MHz)\tFilename')
    else:
        summary_file = open(summary_fname, 'a+')
    summary_file.write("\n{}\t{}".format(FWHM.to('MHz').magnitude, data_fname))
    summary_file.close()


def _ensure_photo_copied(full_photo_name):
    # Place copy of photo in 'pics' dir one level up for easy comparison
    if not os.path.exists(full_photo_name):
        return
    full_data_dir, photo_basename = os.path.split(full_photo_name)
    root, ext = os.path.splitext(photo_basename)
    one_up_dir, data_dir_basename = os.path.split(full_data_dir)
    full_pics_dir = os.path.join(one_up_dir, 'pics')
    if not os.path.exists(full_pics_dir):
        os.makedirs(full_pics_dir)
    
    full_newphoto_name = os.path.join(full_pics_dir, data_dir_basename + ext)
    if not os.path.exists(full_newphoto_name):
        shutil.copy(full_photo_name, full_newphoto_name)


def fit_ringdown_save(subdir='', trace_num=0, base_dir=r'C:\Users\dodd\Documents\Nate\Data'):
    """
    Read a trace from the scope, save it and fit a ringdown curve.
    
    Parameters
    ----------
    subdir : string
        Subdirectory in which to save the data file.
    trace_num : int
        An index indicating which trace it is.
    base_dir: string
        The path of the toplevel data directory.
    """
    scope = scopes.scope(scopes.SCOPE_A)
    x, y = scope.get_data(1)
    
    filename = 'Ringdown {:02}.csv'.format(trace_num)
    full_filename = os.path.join(base_dir, date.today().isoformat(), subdir, filename)
    _save_data(x, y, full_filename)
    
    FWHM = guided_ringdown_fit(x, y)
    _save_summary(full_filename, FWHM)
    print("FWHM = {}".format(FWHM))

def fit_ringdown(scope, channel=1, FSR=None):
    scope = scopes.scope(scope) # This is absurd
    x, y = scope.get_data(channel)
    FWHM = guided_ringdown_fit(x, y)
    print("FWHM = {}".format(FWHM))
    if FSR:
        FSR = u.Quantity(FSR)
        print("Finesse = {:,.0F}".format(float(FSR/FWHM)))
    

def fit_scan_save(EOM_freq, subdir='', trace_num=0, base_dir=r'C:\Users\dodd\Documents\Nate\Data'):
    scope = scopes.scope(scopes.SCOPE_A)
    
    EOM_freq = u.Quantity(EOM_freq)
    x, y = scope.get_data(1)
    comment = "EOM frequency: {}".format(EOM_freq)
    
    filename = 'Scan {:02}.csv'.format(trace_num)
    full_data_dir = os.path.join(base_dir, date.today().isoformat(), subdir)
    full_filename = os.path.join(full_data_dir, filename)
    _save_data(x, y, full_filename, comment)
    
    params = guided_trace_fit(x, y, EOM_freq)
    _save_summary(full_filename, params['FWHM'])
    _ensure_photo_copied(os.path.join(full_data_dir, 'folder.jpg'))
    print("FWHM = {}".format(params['FWHM']))

def fit_scan(EOM_freq, scope, channel=1):
    scope = scopes.scope(scope) # This is absurd
    EOM_freq = u.Quantity(EOM_freq)
    x, y = scope.get_data(channel)
    params = guided_trace_fit(x, y, EOM_freq)
    print("FWHM = {}".format(params['FWHM']))

def diff(unitful_array):
    return Q_(np.diff(unitful_array.magnitude), unitful_array.units)

def FSRs_from_mode_wavelengths(wavelengths):
    return np.abs(diff(u.c / wavelengths)).to('GHz')

def find_FSR():
    wavelengths = []
    while True:
        raw = raw_input('Input wavelength (nm): ')
        if not raw:
            break
        wavelengths.append(float(raw))
    wavelengths = wavelengths * u.nm
    FSRs = FSRs_from_mode_wavelengths(wavelengths)
    print(FSRs)
    print('Mean: {}'.format(np.mean(FSRs)))

TOP_CAM_SERIAL = '4002856484'
SIDE_CAM_SERIAL = '4002862589'

def do_ringdown_set(set_name, base_dir=r'C:\Users\dodd\Documents\Nate\Data'):
    set_dir = os.path.join(base_dir, date.today().isoformat(), set_name)
    if not os.path.exists(set_dir):
        os.makedirs(set_dir)

    # Block until light is turned on
    raw_input('Please turn on light then press [ENTER]: ')

    from .drivers.cameras.uc480 import get_camera, cameras
    top_cam = get_camera(serial=TOP_CAM_SERIAL)
    side_cam = get_camera(serial=SIDE_CAM_SERIAL)
    top_cam.open()
    #top_cam.load_stored_parameters(1)
    top_cam.load_stored_parameters(1)
    top_cam.save_frame(os.path.join(set_dir, 'Top.jpg'))
    top_cam.close()
    side_cam.open()
    side_cam.load_stored_parameters(1)
    side_cam.save_frame(os.path.join(set_dir, 'Side.jpg'))
    side_cam.close()

    scope = scopes.scope(scopes.SCOPE_A)
    fname = 'Ringdown {:02}.csv'
    trace_num = 0
    cum_FWHM = 0 * u.MHz
    print("-------------Enter d[one] to stop taking data-------------")
    while True:
        s = raw_input('Press [ENTER] to process ringdown {}: '.format(trace_num))
        if s and s[0].lower() == 'd':
            break
        x, y = scope.get_data(channel=1)
        full_filename = os.path.join(set_dir, fname.format(trace_num))
        _save_data(x, y, full_filename)

        FWHM = guided_ringdown_fit(x, y)
        _save_summary(full_filename, FWHM)
        print("-------------------------------------- FWHM = {}".format(FWHM))
        cum_FWHM += FWHM
        trace_num += 1
    print('Mean FWHM: {}'.format(cum_FWHM/trace_num))

def get_photo_fnames():
    basedir = r'C:\Users\dodd\Documents\Nate\Data'
    fnames = []
    w = os.walk(basedir)
    w.next()
    for root, dirs, files in w:
        num_subdirs = len(dirs)
        for i in range(num_subdirs):
            root, dirs, files = w.next()
            files = [os.path.join(root, f) for f in files if (f.lower() in ['top.jpg','folder.jpg'])]
            fnames.extend(files)
    return fnames
