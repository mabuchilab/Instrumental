# -*- coding: utf-8 -*-
import os
import os.path
import shutil
from datetime import date, datetime
import numpy as np

from .fitting import guided_trace_fit, ringdown_fit
from . import u
from .drivers import SCOPE_A

# Fix for Python 2
try: input = raw_input
except NameError: pass

prev_data_fname = ''

def save_data(time, signal, full_filename, comment=''):
    full_dir = os.path.dirname(full_filename)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)
    
    timestamp = "Data saved {}".format(datetime.now().isoformat(' '))
    labels = "Time ({}), Signal ({})".format(time.units, signal.units)
    header = '\n'.join([timestamp, comment, '', labels])
    
    data = np.array((time.magnitude, signal.magnitude)).T
    np.savetxt(full_filename, data, header=header, delimiter=",")


def save_ringdown(time, signal, full_filename):
    full_dir = os.path.dirname(full_filename)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir)
    
    timestamp = "Data saved{}".format(datetime.now().isoformat(' '))
    labels = "Time ({}), Signal ({})".format(time.units, signal.units)
    header = '\n'.join([timestamp, '', labels])
    
    data = np.array((time.magnitude, signal.magnitude)).T
    np.savetxt(full_filename, data, header=header, delimiter=",")


def save_summary(full_data_filename, FWHM):
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


def ensure_photo_copied(full_photo_name):
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


def fit_ringdown(subdir='', trace_num=0, base_dir=r'C:\Users\dodd\Documents\Nate\Data'):
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
    scope = SCOPE_A
    x, y = scope.get_data(1)
    
    filename = 'Ringdown {:02}.csv'.format(trace_num)
    full_filename = os.path.join(base_dir, date.today().isoformat(), subdir, filename)
    save_data(x, y, full_filename)
    
    FWHM = ringdown_fit(x, y)
    save_summary(full_filename, FWHM)
    print("FWHM = {}".format(FWHM))
    

def fit_scan(EOM_freq, subdir='', trace_num=0, base_dir=r'C:\Users\dodd\Documents\Nate\Data'):
    scope = SCOPE_A
    
    EOM_freq = u.Quantity(EOM_freq)
    x, y = scope.get_data(1)
    comment = "EOM frequency: {}".format(EOM_freq)
    
    filename = 'Scan {:02}.csv'.format(trace_num)
    full_data_dir = os.path.join(base_dir, date.today().isoformat(), subdir)
    full_filename = os.path.join(full_data_dir, filename)
    save_data(x, y, full_filename, comment)
    
    params = guided_trace_fit(x, y, EOM_freq)
    save_summary(full_filename, params['FWHM'])
    ensure_photo_copied(os.path.join(full_data_dir, 'folder.jpg'))
    print("FWHM = {}".format(params['FWHM']))