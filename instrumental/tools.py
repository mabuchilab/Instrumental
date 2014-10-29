# -*- coding: utf-8 -*-
import os
import os.path
import shutil
import warnings
from datetime import date, datetime
import numpy as np
import instrumental.plotting as plt
from matplotlib import animation

from .fitting import guided_trace_fit, guided_ringdown_fit
from . import u, Q_, conf, instrument
from .drivers import scopes

# Fix for Python 2
try:
    input = raw_input
except NameError:
    pass

prev_data_fname = ''


class DataSession(object):
    """A data-taking session.

    Useful for organizing, saving, and live-plotting data while (automatically
    or manually) taking it.
    """
    def __init__(self, name, meas_gen, overwrite=False):
        """Create a DataSession.

        Parameters
        ----------
        name : str
            The name of the session. Used for naming the saved data file.
        meas_gen : generator
            A generator that, when iterated through, returns individual
            measurements as dicts. Each dict key is a string that is the name
            of what's being measured, and its matching value is the
            corresponding quantity.
            Most often you'll want to create this generator by writing a
            generator function.
        overwrite : bool
            If True, data with the same filename will be overwritten. Defaults
            to False.
        """
        self.name = name
        self.overwrite = overwrite
        self.data_dir = self._find_data_dir()
        self.start_time = datetime.now()
        self.end_time = None
        self.measurement_num = 1
        self.meas_dict = {}
        self.has_plot = False
        self.axs = []
        self.lines = []
        self.plotvars = []
        self.meas_gen = meas_gen

    def _add_measurement(self, meas_dict):
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

                if name not in self.meas_dict:
                    self.meas_dict[name] = Q_(np.array([value.magnitude]), value.units)
                else:
                    self.meas_dict[name] = qappend(self.meas_dict[name], value)
        self.save_summary(overwrite=True)

    def _default_format(self, arr):
        """ Returns the default format string for an array of this type """
        kind = np.asarray(arr).dtype.kind
        if kind == 'i':
            fmt = '%d'
        else:
            fmt = '%.8e'
        return fmt

    def save_summary(self, overwrite=None):
        arrays, labels, fmt = [], [], []

        # Extract names and units to make the labels
        for name, qarr in self.meas_dict.items():
            unit = qarr.units
            labels.append('{} ({})'.format(name, unit))
            arrays.append(qarr.magnitude)
            fmt.append(self._default_format(qarr.magnitude))

        if not arrays:
            warnings.warn('No data input, not saving anything...')
            return

        filename = self._conflict_handled_filename("Summary.csv", overwrite)
        with open(filename, 'w') as f:
            # TODO: Warn if overwriting file
            # Write the 'header'
            f.write("# Data saved {}\n".format(datetime.now().isoformat(' ')))
            f.write("\n")
            f.write('\t'.join(labels) + "\n")

            # Write the data
            data = np.array(arrays).T
            np.savetxt(f, data, fmt=fmt, delimiter='\t')

    def create_plot(self, vars, **kwargs):
        """Create a plot of the DataSession.

        This plot is live-updated with data points as you take them.

        Parameters
        ----------
        vars : list of tuples
            vars to plot. Each tuple corresponds to a data series, with
            x-data, y-data, and optional format string. This is meant to
            be reminiscent of matplotlib's plot function. The x and y data can
            each either be a string (representing the variable in the measurement
            dict with that name) or a function that takes kwargs with the name
            of those in the measurement dict and returns its computed value.
        **kwargs : keyword arguments
            used for formatting the plot. These are passed directly to the plot
            function. Useful for e.g. setting the linewidth.
        """
        self.has_plot = True
        self.plotvars = self._parse_plotvars(vars)
        self.plot_kwargs = kwargs

        self.fig = plt.figure()
        ax = plt.axes()
        for var_triple in self.plotvars:
            x, y, fmt = var_triple

            if self.meas_dict:
                xval, yval = x(**self.meas_dict), y(**self.meas_dict)
                line, = ax.plot(xval, yval, fmt, **self.plot_kwargs)
                ax.set_xlabel('{} ({}s)'.format(x.name, xval.units))
                ax.set_ylabel('{} ({}s)'.format(y.name, yval.units))
            else:
                line, = ax.plot([], [], fmt, **self.plot_kwargs)
                ax.set_xlabel(x.name)
                ax.set_ylabel(y.name)
            self.axs.append(ax)
            self.lines.append(line)

    def _parse_plotvars(self, vars):
        plotvars = []

        # Helper to make sure the lambdas close over the right key
        def makefun(key):
            return lambda **kwargs: kwargs[key]

        if isinstance(vars[0], basestring):
            # Vars wasn't nested; nest it and retry
            return self._parse_plotvars([vars])

        for var_tuple in vars:
            plotvar_triple = []
            plotvars.append(plotvar_triple)
            for var in var_tuple[:2]:
                if isinstance(var, basestring):
                    # Convert var string to a function
                    var_func = makefun(var)
                    var_func.name = var
                    plotvar_triple.append(var_func)
                elif callable(var):
                    plotvar_triple.append(var)
                else:
                    raise Exception("`vars` must contain strings or functions")

            # Handle optional format string
            if len(var_tuple) == 3:
                fmt = var_tuple[2]
            else:
                fmt = ''
            plotvar_triple.append(fmt)

        return plotvars

    def start(self):
        """Start collecting data.

        This function blocks until all data has been collected.
        """
        if self.has_plot:
            # Set up animation scaffolding
            def init():
                return self.lines

            def animate(i):
                meas = next(self.meas_gen)
                self._add_measurement(meas)

                for var_triple, ax, line in zip(self.plotvars, self.axs, self.lines):
                    x, y, fmt = var_triple
                    xval, yval = x(**self.meas_dict), y(**self.meas_dict)
                    line.set_xdata(xval)
                    line.set_ydata(yval)
                    ax.set_xlabel('{} ({}s)'.format(x.name, xval.units))
                    ax.set_ylabel('{} ({}s)'.format(y.name, yval.units))
                    # TODO: fix redundancy for multiple lines on one axis
                    ax.relim()
                    ax.autoscale_view()
                return self.lines

            # Need to keep a reference to anim for the plot to work properly
            # NOTE: We want this to run as fast as possible, but Windows (with
            # QT?) has problems updating the graph if the specified interval is
            # too short We'll use 50ms for now since it seems to work...
            anim = animation.FuncAnimation(self.fig, animate, init_func=init,
                                           blit=False, repeat=False, interval=50)
            plt.show()
        else:
            try:
                i = 0
                while True:
                    meas = next(self.meas_gen)
                    self._add_measurement(meas)
                    i += 1
            except StopIteration:
                pass

    def _conflict_handled_filename(self, fname, overwrite=None):
        if overwrite is None:
            overwrite = self.overwrite

        # fname is name of file within data_dir
        full_fname = os.path.join(self.data_dir, fname)
        is_conflict = os.path.exists(full_fname)
        if is_conflict:
            if overwrite:
                print("Warning: Overwriting file {}".format(fname))
            else:
                i = 1
                new_full_fname = full_fname
                while os.path.exists(new_full_fname):
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
        if not self.overwrite:
            while os.path.exists(data_dir):
                alt_session_subdir = '{} {}'.format(session_subdir, i)
                data_dir = os.path.join(base_dir, date_subdir, alt_session_subdir)
                i += 1

        if i > 1:
            print('Session name "{}" used already. Using "{}" instead.'.format(
                session_subdir, alt_session_subdir))
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir


def qappend(arr, values, axis=None):
    """ Append values to the end of an array-valued Quantity. """
    new_mag = np.append(arr.magnitude, values.to(arr.units).magnitude, axis)
    return Q_(new_mag, arr.units)


def load_data(fname, delimiter='\t'):
    line = ''
    with open(fname) as f:
        while True:
            prev_line = line
            line = f.readline()
            if line == '':
                return None  # EOF before any data

            line = line.strip()
            if line and line[0] != '#':
                # First non-empty non-comment line has the names and units
                break

        # Read rest of file using numpy's data file parser
        arr = np.loadtxt(f, delimiter=delimiter)

        header = prev_line.strip(' #')

        meas_dict = {}
        for heading, col in zip(header.split(delimiter), arr.T):
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


def fit_ringdown_save(subdir='', trace_num=0, base_dir=None):
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
    if base_dir is None:
        base_dir = conf.prefs['data_directory']
    scope = scopes.scope(scopes.SCOPE_A)
    x, y = scope.get_data(1)

    filename = 'Ringdown {:02}.csv'.format(trace_num)
    full_filename = os.path.join(base_dir, date.today().isoformat(), subdir, filename)
    _save_data(x, y, full_filename)

    FWHM = guided_ringdown_fit(x, y)
    _save_summary(full_filename, FWHM)
    print("FWHM = {}".format(FWHM))


def fit_ringdown(scope, channel=1, FSR=None):
    scope = instrument(scope)
    x, y = scope.get_data(channel)
    FWHM = guided_ringdown_fit(x, y)
    print("FWHM = {}".format(FWHM))
    if FSR:
        FSR = u.Quantity(FSR)
        print("Finesse = {:,.0F}".format(float(FSR/FWHM)))


def fit_scan_save(EOM_freq, subdir='', trace_num=0, base_dir=None):
    if base_dir is None:
        base_dir = conf.prefs['data_directory']
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
    scope = scopes.scope(scope)  # This is absurd
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


def do_ringdown_set(set_name, base_dir=None):
    if base_dir is None:
        base_dir = conf.prefs['data_directory']
    set_dir = os.path.join(base_dir, date.today().isoformat(), set_name)
    if not os.path.exists(set_dir):
        os.makedirs(set_dir)

    # Block until light is turned on
    raw_input('Please turn on light then press [ENTER]: ')

    from .drivers.cameras.uc480 import get_camera
    top_cam = get_camera(serial=TOP_CAM_SERIAL)
    side_cam = get_camera(serial=SIDE_CAM_SERIAL)
    top_cam.open()
    # top_cam.load_stored_parameters(1)
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
    basedir = conf.prefs['data_directory']
    fnames = []
    w = os.walk(basedir)
    w.next()
    for root, dirs, files in w:
        num_subdirs = len(dirs)
        for i in range(num_subdirs):
            root, dirs, files = w.next()
            files = [os.path.join(root, f) for f in files
                     if (f.lower() in ['top.jpg', 'folder.jpg'])]
            fnames.extend(files)
    return fnames
