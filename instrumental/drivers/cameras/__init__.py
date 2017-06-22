# -*- coding: utf-8 -*-
# Copyright 2013-2016 Nate Bogdanowicz
"""
Package containing a driver module/class for each supported camera type.
"""
import abc
import json
import os.path
import numpy as np
from .. import Instrument
from ... import Q_, conf
from ...errors import Error



class Camera(Instrument):
    """A generic camera device.

    Camera driver internals can often be quite different; however, Instrumental defines a few basic
    concepts that all camera drivers should have.

    There are two basic modes: *finite* and *continuous*.

    In *finite* mode, a camera performs a capture sequence, returning one or more images all at
    once, when the sequence is finished.

    In *continuous* or *live* mode, the camera continuously retrieves images until it is manually
    stopped. This mode can be used e.g. to make a GUI that looks at a live view of the camera. The
    process looks like this::

        >>> cam.start_live_video()
        >>> while not_done():
        >>>     frame_ready = cam.wait_for_frame()
        >>>     if frame_ready:
        >>>         arr = cam.latest_frame()
        >>>         do_stuff_with(arr)
        >>> cam.stop_live_video()
    """

    DEFAULT_KWDS = dict(n_frames=1, vbin=1, hbin=1, exposure_time=Q_('10ms'), gain=0, width=None,
                        height=None, cx=None, cy=None, left=None, right=None, top=None, bot=None,
                        fix_hotpixels=False)

    @abc.abstractproperty
    def width(self):
        """Width of the camera image in pixels"""
        pass

    @abc.abstractproperty
    def height(self):
        """Height of the camera image in pixels"""
        pass

    @abc.abstractproperty
    def max_width(self):
        """Max settable width of the camera image, given current binning/subpixel settings"""
        pass

    @abc.abstractproperty
    def max_height(self):
        """Max settable height of the camera image, given current binning/subpixel settings"""
        pass

    _hot_pixels = None
    _defaults = None

    @abc.abstractmethod
    def start_capture(self, **kwds):
        """Start a capture sequence and return immediately

        Depending on your camera-specific shutter/trigger settings, this will either start the
        exposure immediately or ready the camera to start on an explicit (hardware or software)
        trigger.

        It can be useful to invoke ``capture()`` and ``get_captured_image()`` explicitly if you
        expect the capture sequence to take a long time and you'd like to perform some operations
        while you wait for the camera::

            >>> cam.capture()
            >>> do_other_useful_stuff()
            >>> arr = cam.get_captured_image()

        See `grab_image()` for the set of available kwds.
        """

    @abc.abstractmethod
    def get_captured_image(self, timeout='1s', copy=True):
        """Get the image array(s) from the last capture sequence

        Returns an image numpy array (or tuple of arrays for a multi-exposure sequence). The array
        has shape *(height, width)* for grayscale images, and *(height, width, 3)* for RGB images.
        Typically the dtype will be `uint8`, or sometimes `uint16` in the case of 16-bit
        monochromatic cameras.

        Parameters
        ----------
        timeout : Quantity([time]) or None, optional
            Max time to wait for wait for the image data to be ready. If *None*, will block
            forever. If timeout is exceeded, a TimeoutError will be raised.
        copy : bool, optional
            Whether to copy the image memory or directly reference the underlying buffer. It is
            recommended to use *True* (the default) unless you know what you're doing.
        """

    @abc.abstractmethod
    def grab_image(self, timeouts='1s', copy=True, **kwds):
        """Perform a capture and return the resulting image array(s)

        This is essentially a convenience function that calls `start_capture()` then
        `get_captured_image()`. See `get_captured_image()` for information about the returned
        array(s).

        Parameters
        ----------
        timeouts : Quantity([time]) or None, optional
            Max time to wait for wait for the image data to be ready. If *None*, will block
            forever. If timeout is exceeded, a TimeoutError will be raised.
        copy : bool, optional
            Whether to copy the image memory or directly reference the underlying buffer. It is
            recommended to use *True* (the default) unless you know what you're doing.

        You can specify other parameters of the capture as keyword arguments. These include:

        Other Parameters
        ----------------
        n_frames : int
            Number of exposures in the sequence
        vbin : int
            Vertical binning
        hbin : int
            Horizontal binning
        exposure_time : Quantity([time])
            Duration of each exposure
        width : int
            Width of the ROI
        height : int
            Height of the ROI
        cx : int
            X-axis center of the ROI
        cy : int
            Y-axis center of the ROI
        left : int
            Left edge of the ROI
        right : int
            Right edge of the ROI
        top : int
            Top edge of the ROI
        bot : int
            Bottom edge of the ROI
        """

    @abc.abstractmethod
    def start_live_video(self, **kwds):
        """Start live video mode

        Once live video mode has been started, images will automatically and continuously be
        acquired. You can check if the next frame is ready by using `wait_for_frame()`, and access
        the most recent image's data with `get_captured_image()`.

        See `grab_image()` for the set of available kwds.
        """

    @abc.abstractmethod
    def stop_live_video(self):
        """Stop live video mode"""

    @abc.abstractmethod
    def wait_for_frame(self, timeout=None):
        """Wait until the next frame is ready (in live mode)

        Blocks and returns True once the next frame is ready, False if the timeout was reached.
        Using a timeout of 0 simply polls to see if the next frame is ready.

        Parameters
        ----------
        timeout : Quantity([time]), optional
            How long to wait for wait for the image data to be ready. If *None* (the default), will
            block forever.

        Returns
        -------
        frame_ready : bool
            *True* if the next frame is ready, *False* if the timeout was reached.
        """

    @abc.abstractmethod
    def latest_frame(self, copy=True):
        """Get the latest image frame in live mode

        Returns the image array received on the most recent successful call to `wait_for_frame()`.

        Parameters
        ----------
        copy : bool, optional
            Whether to copy the image memory or directly reference the underlying buffer. It is
            recommended to use *True* (the default) unless you know what you're doing.
        """

    def set_defaults(self, **kwds):
        if self._defaults is None:
            self._defaults = self.DEFAULT_KWDS.copy()

        for k in kwds:
            if k not in self._defaults:
                raise Error("Unknown parameter '{}'".format(k))
        self._defaults.update(kwds)

    def _handle_kwds(self, kwds, fill_coords=True):
        """Don't reimplement this, it's super-annoying"""
        if self._defaults is None:
            self._defaults = self.DEFAULT_KWDS.copy()

        bad_kwds = [k for k in kwds if k not in self._defaults]
        if bad_kwds:
            raise Error("Unknown parameters {}".format(bad_kwds))

        for k, v in self._defaults.items():
            kwds.setdefault(k, v)

        if fill_coords:
            self.fill_all_coords(kwds, ('width', 'cx', 'left', 'right'))
            self.fill_all_coords(kwds, ('height', 'cy', 'top', 'bot'))

    def fill_all_coords(self, kwds, names):
        n_args = sum(kwds[n] is not None for n in names)
        if n_args == 0:
            kwds[names[0]] = getattr(self, 'max_' + names[0])  # max_width or max_height
            kwds[names[2]] = 0  # left or top = 0
        elif n_args == 1:
            max_width = getattr(self, 'max_' + names[0])
            if kwds[names[2]] is not None:  # Left given
                kwds[names[3]] = max_width
            elif kwds[names[3]] is not None:  # Right given
                kwds[names[2]] = 0
            elif kwds[names[1]] is not None:  # Center given
                if kwds[names[1]] > max_width/2:
                    kwds[names[3]] = max_width  # Bounded by the right
                else:
                    kwds[names[2]] = 0  # Bounded by the left
            else:  # Width given
                kwds[names[1]] = max_width/2  # Centered
        elif n_args != 2:
            raise ValueError("Only two of {} should be provided".format(names))

        values = [kwds[n] for n in names]
        width, cx, left, right = values

        # NOTES
        # For cx=1, width=1 -> left=1, right=2
        # For cx=1, width=2 -> left=0, right=2
        # So an odd rectangle always rounds to add a pixel at the right (bottom)
        # i.e. cx rounds down
        if left is not None:
            if right is not None:
                width = right - left
                cx = left + width/2
            elif cx is not None:
                # Assume an even width
                right = cx + (cx - left)
                width = right - left
            elif width is not None:
                right = left + width
                cx = left + width/2
        elif right is not None:
            if cx is not None:
                # Assume an even width
                width = (right - cx) * 2
                left = right - width
            elif width is not None:
                left = right - width
                cx = left + width/2
        else:
            left = cx - width/2
            right = left + width

        kwds.update(zip(names, (width, cx, left, right)))

    def find_hot_pixels(self, stddevs=10, **kwds):
        """Generate the list of hot pixels on the camera sensor"""
        img = self.grab_image(**kwds)
        avg = np.mean(img)
        stddev = np.sqrt(np.var(img))

        threshold = avg + stddevs*stddev
        pixels = np.argwhere(img > threshold)

        # Cast to avoid the indices being longs in Py2
        self._hot_pixels = pixels.astype('int32', copy=False).tolist()

    def save_hot_pixels(self, path=None):
        """Save a file listing the hot pixels"""
        if self._hot_pixels is None:
            raise Error("No existing list of hot pixels to save. Generate one first by using "
                        "`find_hot_pixels()`")

        if not path:
            if self._alias:
                path = os.path.join(conf.user_conf_dir, 'hotpixel_{}.json'.format(self._alias))
            else:
                path = 'hotpixel.json'

        with open(path, 'w') as f:
            json.dump({'hot_pixels': self._hot_pixels}, f)

        new_path = os.path.abspath(path)
        if self._alias and self._param_dict.get('hotpixel_file', None) != new_path:
            self._param_dict['hotpixel_file'] = new_path
            self.save_instrument(self._alias, force=True)

    def _correct_hot_pixels(self, img):
        """Correct hot pixels by averaging their neighbors"""
        if self._hot_pixels is None:
            raise Error("Could not correct hot pixels because we have no existing list of hot "
                        "pixels. Generate one first by using `find_hot_pixels()`")

        if len(img.shape) != 2:
            raise NotImplementedError("Hot pixel correction currently implemented only for "
                                      "monochrome sensors")

        # TODO: Probably shouldn't include adjacent hot pixels
        img = img.copy()
        for y, x in self._hot_pixels:
            left = max(0, x-1)
            right = min(img.shape[1], x+2)
            top = max(0, y-1)
            bot = min(img.shape[0], y+2)
            img[y, x] = (img[top:bot, left:right].sum() - img[y, x])/((bot-top)*(right-left)-1)
        return img


def _init_instrument(cam, params):
    if 'hotpixel_file' in params:
        with open(params['hotpixel_file']) as f:
            hotpixel_data = json.load(f)
            cam._hot_pixels = hotpixel_data['hot_pixels']
