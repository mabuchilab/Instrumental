# -*- coding: utf-8 -*-
# Copyright 2013-2015 Nate Bogdanowicz
"""
Package containing a driver module/class for each supported camera type.
"""
import abc
from .. import Instrument


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
    __metaclass__ = abc.ABCMeta

    #: Width of the camera image in pixels
    width = None

    #: Height of the camera image in pixels
    height = None

    @abc.abstractmethod
    def start_capture(self, **kwargs):
        """Start a capture sequence and return immediately

        Depending on your camera-specific shutter/trigger settings, this will either start the
        exposure immediately or ready the camera to start on an explicit (hardware or software)
        trigger.

        It can be useful to invoke ``capture()`` and ``image_array()`` explicitly if you expect the
        capture sequence to take a long time and you'd like to perform some operations while you
        wait for the camera::

            >>> cam.capture()
            >>> do_other_useful_stuff()
            >>> arr = cam.image_array()

        See `grab_image()` for the set of available kwargs.
        """

    @abc.abstractmethod
    def captured_image(self, timeout='1s', copy=True):
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
    def grab_image(self, timeouts='1s', copy=True, **kwargs):
        """Perform a capture and return the resulting image array(s)

        This is essentially a convenience function that calls `start_capture()` then
        `image_array()`. See `image_array()` for information about the returned array(s).

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
    def start_live_video(self, **kwargs):
        """Start live video mode

        Once live video mode has been started, images will automatically and continuously be
        acquired. You can check if the next frame is ready by using `wait_for_frame()`, and access
        the most recent image's data with `image_array()`.

        See `grab_image()` for the set of available kwargs.
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
