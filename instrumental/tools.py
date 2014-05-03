# -*- coding: utf-8 -*-
import os
import os.path
import shutil
import warnings
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
    def __init__(self, name, overwrite=False):
        self.name = name
        self.overwrite = overwrite
        self.data_dir = self._find_data_dir()
        self.start_time = datetime.now()
        self.end_time = None
        self.measurement_num = 1
        self.meas_list = {}

    def add_measurement(self, meas_dict, comment=None):
        """
        Parameters
        ----------
        meas_dict : dict
            Measurement `dict` whose keys are strings representing the names
            of measured quantities, and whose values are pint Quantity objects
            representing the value of each measurement.
        """
        filename_try = "Measurement {}.csv".format(self.measurement_num)
        filename = self._conflict_handled_filename(filename_try)
        self.measurement_num += 1
        with open(filename, 'w') as f:
            # TODO: Warn if overwriting file
            f.write('# Data saved {}\n\n'.format(datetime.now().isoformat(' ')))
            for name, value in meas_dict.items():
                fmt = self._default_format(value.magnitude)
                f.write('{} = {}\n'.format(name, fmt) % value.magnitude)

                if name not in self.meas_list:
                    self.meas_list[name] = Q_(np.array([value.magnitude]), value.units)
                else:
                    self.meas_list[name] = qappend(self.meas_list[name], value)

    def _default_format(self, arr):
        """ Returns the default format string for an array of this type """
        kind = np.asarray(arr).dtype.kind
        if kind == 'i':
            fmt = '%d'
        else:
            fmt = '%.8e'
        return fmt

    def save_summary(self, comment=None):
        arrays, labels, fmt = [], [], []

        # Extract names and units to make the labels
        for name, qarr in self.meas_list.items():
            unit = qarr.units
            labels.append('{} ({})'.format(name, unit))
            arrays.append(qarr.magnitude)
            fmt.append(self._default_format(qarr.magnitude))

        filename = self._conflict_handled_filename("Summary.csv")
        with open(filename, 'w') as f:
            # TODO: Warn if overwriting file
            # Write the 'header'
            f.write("# Data saved {}\n".format(datetime.now().isoformat(' ')))
            f.write("\n")
            f.write(', '.join(labels) + "\n")

            # Write the data
            data = np.array(arrays).T
            np.savetxt(f, data, fmt=fmt, delimiter=',')

    def _conflict_handled_filename(self, fname):
        # fname is name of file within data_dir
        full_fname = os.path.join(self.data_dir, fname)
        is_conflict = os.path.exists(full_fname)
        if is_conflict:
            if self.overwrite:
                print("Warning: Overwriting file {}".format(fname))
            else:
                i = 1
                new_full_fname = full_fname
                while os.path.exists(new_filename):
                    new_fname = '({}) {}'.format(i, fname)
                    new_full_fname = os.path.join(self.data_dir, new_fname)
                    i += 1
                print('Filename "{}" used already. Using "{}" instead.'.format(
                    fname, new_fname))
                full_fname = new_full_fname
        return full_fname


    def _quantity_list_to_array(self, qlist):
        # I feel like there should already exist a function for this...
        units = qlist[0].units
        mags = np.array([q.to(units).magnitude for q in qlist])
        return Q_(mags, units)

    def _find_data_dir(self):
        base_dir = conf.prefs['data_directory']
        date_subdir = date.today().isoformat()
        session_subdir = self.name

        i = 1
        data_dir = os.path.join(base_dir, date_subdir, session_subdir)
        while os.path.exists(data_dir):
            alt_session_subdir = '{} {}'.format(session_subdir, i)
            data_dir = os.path.join(base_dir, date_subdir, alt_session_subdir)
            i += 1

        if i > 1:
            print('Session name "{}" used already. Using "{}" instead.'.format(
                session_subdir, alt_session_subdir))
        os.makedirs(data_dir)
        return data_dir


def qappend(arr, values, axis=None):
    """ Append values to the end of an array-valued Quantity. """
    new_mag = np.append(arr.magnitude, values.to(arr.units).magnitude, axis)
    return Q_(new_mag, arr.units)


def load_data(fname, delimiter=','):
    with open(fname) as f:
        while True:
            line = f.readline()
            if line == '':
                return None  # EOF before any data

            line = line.strip()
            if line and line[0] != '#':
                # First non-empty non-comment line has the names and units
                break

        # Read rest of file using numpy's data file parser
        arr = np.loadtxt(f, delimiter=delimiter)

        meas_dict = {}
        for heading, col in zip(line.split(','), arr.T):
            left, right = heading.split('(')
            name, units = left.strip(), right.strip(')')
            meas_dict[name] = Q_(col, units)
        return meas_dict


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
