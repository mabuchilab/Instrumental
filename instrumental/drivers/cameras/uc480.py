# -*- coding: utf-8  -*-
# Copyright 2013 Nate Bogdanowicz
"""
Driver for Thorlabs DCx cameras. May be compatible with iDS cameras that use
uEye software. Currently Windows-only, but Linux support should be
possible to implement if desired.
"""

from ctypes import WinDLL, pointer, POINTER, c_char, c_char_p, addressof, cast
from ctypes.wintypes import DWORD, INT, ULONG, DOUBLE, HWND
import os.path
from .uc480_constants import *
from .uc480_structs import *

HCAM = DWORD
NULL = POINTER(HWND)()
lib = WinDLL('uc480_64')

def cameras():
    """
    Get a list of all cameras currently attached.
    """
    cams = []
    num = INT()
    if lib.is_GetNumberOfCameras(pointer(num)) == IS_SUCCESS:
        if num >= 1:
            cam_list = create_camera_list(num)()
            cam_list.dwCount = ULONG(num.value) # This is stupid

            if lib.is_GetCameraList(pointer(cam_list)) == IS_SUCCESS:
                ids = []
                repeated = []
                for info in cam_list.ci:
                    id = info.dwCameraID
                    if id in ids:
                        repeated.append(id)
                    ids.append(id)

                if not repeated:
                    for info in cam_list.ci:
                        cams.append(Camera(info))
                else:
                    print("Some cameras have duplicate IDs. Uniquifying IDs now...")
                    # Choose IDs that haven't been used yet
                    potential_ids = [i for i in range(1,len(ids)+1) if i not in ids]
                    for id in repeated:
                        new_id = potential_ids.pop(0)
                        print("Trying to set id from {} to {}".format(id, new_id))
                        _id = HCAM(id)
                        ret = lib.is_InitCamera(pointer(_id), NULL)
                        if not ret == IS_SUCCESS:
                            print("Error connecting to camera {}".format(id))
                            return None # Avoid infinite recursion
                        else:
                            ret = lib.is_SetCameraID(_id, INT(new_id))
                            if not ret == IS_SUCCESS:
                                print("Error setting the camera id")
                                return None # Avoid infinite recursion
                    # All IDs should be fixed now, let's retry
                    cams = cameras()
            else:
                print("Error getting camera list")
    else:
        print("Error getting number of attached cameras")
    return cams

def get_camera(**kwargs):
    """
    Get a camera by attribute. Returns the first attached camera that
    matches the ``\*\*kwargs``. E.g. passing serial='abc' will return a camera
    whose serial number is 'abc', or None if no such camera is connected.
    """
    cams = cameras()
    if not cams:
        return None
    if not kwargs:
        return cams[0]
    
    kwarg = kwargs.items()[0]
    if kwarg[0] not in ['id', 'serial', 'model']:
        return None

    for cam in cams:
        # TODO: Maybe cast to allow comparison of strings and ints, etc.
        if getattr(cam, kwarg[0]) == kwarg[1]:
            return cam
    return None


class Camera(object):
    """
    A uc480-supported Camera. Get access to a Camera using cameras() and
    get_camera(), not using the constructor directly.
    """
    def __init__(self, cam_info):
        # Careful: cam_info will not update to reflect changes, it's a snapshot
        self._info = cam_info
        self._id = HCAM(cam_info.dwCameraID)
        self._in_use = False
        self._width, self._height = INT(), INT()
        self._color_depth = INT()
        self._color_mode = INT()
        self._p_img_mem = POINTER(c_char)() # Never directly modify this pointer!
        self._memid = INT()
        self._list_p_img_mem = None
        self._list_memid = None

    def __del__(self):
        if self._in_use:
            self.close() # In case someone forgot to close()

    def set_auto_exposure(self, enable=True):
        ret = lib.is_SetAutoParameter(self._id, IS_SET_ENABLE_AUTO_SHUTTER,
                                      pointer(INT(enable)), NULL)
        if ret != IS_SUCCESS:
            print("Failed to set auto exposure property")

    def load_stored_parameters(self, set_num):
        if set_num in [1, 2]:
            ret = lib.is_LoadParameters(self._id, c_char_p("/cam/set{}".format(set_num)))
            if ret != IS_SUCCESS:
                print("Failed to load internally stored parameters")
            else:
                # Reset original display color mode
                lib.is_GetColorDepth(self._id, pointer(self._color_depth), pointer(self._color_mode))
                lib.is_SetColorMode(self._id, self._color_mode)
        else:
            print("set_num must be either 1 or 2")

    def load_parameter_file(self, filename=None):
        if not filename:
            ptr = NULL
        else:
            ptr = c_char_p(filename)
        ret = lib.is_LoadParameters(self._id, ptr)
        if ret != IS_SUCCESS:
            print("Failed to load parameter file")
        else:
            # Reset original display color mode
            lib.is_GetColorDepth(self._id, pointer(self._color_depth), pointer(self._color_mode))
            lib.is_SetColorMode(self._id, self._color_mode)

    def open(self, num_bufs=1):
        """
        Connect to the camera and set up the image memory.
        """
        ret = lib.is_InitCamera(pointer(self._id), NULL)
        if ret != IS_SUCCESS:
            print("Failed to open camera")
        else:
            self._in_use = True
            if num_bufs == 1:
                self._allocate_image_mem()
            else:
                self._allocate_mem_seq(num_bufs)

    def _allocate_image_mem(self):
        """
        Create and set the image memory.
        """
        self.width, self.height = self._get_max_img_size()

        # Set the save/display color depth to the current Windows setting
        lib.is_GetColorDepth(self._id, pointer(self._color_depth), pointer(self._color_mode))
        lib.is_SetColorMode(self._id, self._color_mode)

        # Allocate and set memory
        lib.is_AllocImageMem(self._id, self._width, self._height, self._color_depth,
                             pointer(self._p_img_mem), pointer(self._memid))
        lib.is_SetImageMem(self._id, self._p_img_mem, self._memid)

        # Initialize display
        lib.is_SetImageSize(self._id, self._width, self._height)
        lib.is_SetDisplayMode(self._id, IS_SET_DM_DIB)

    def _allocate_mem_seq(self, num_bufs):
        """
        Create and setup the image memory for live capture
        """
        self.width, self.height = self._get_max_img_size()

        # Set the save/display color depth to the current Windows setting
        lib.is_GetColorDepth(self._id, pointer(self._color_depth), pointer(self._color_mode))
        lib.is_SetColorMode(self._id, self._color_mode)
        
        self._list_p_img_mem = []
        self._list_memid = []
        for i in range(num_bufs):
            p_img_mem = POINTER(c_char)()
            memid = INT()
            lib.is_AllocImageMem(self._id, self._width, self._height, self._color_depth,
                                 pointer(p_img_mem), pointer(memid))
            lib.is_AddToSequence(self._id, p_img_mem, memid)
            self._list_p_img_mem.append(p_img_mem)
            self._list_memid.append(memid)

        # Initialize display
        lib.is_SetImageSize(self._id, self._width, self._height)
        lib.is_SetDisplayMode(self._id, IS_SET_DM_DIB)

    def _install_event_handler(self):
        import win32event
        self.hEvent = win32event.CreateEvent(None, False, False, '')
        lib.is_InitEvent(self._id, self.hEvent.handle, IS_SET_EVENT_FRAME)
        lib.is_EnableEvent(self._id, IS_SET_EVENT_FRAME)

    def _uninstall_event_handler(self):
        lib.is_DisableEvent(self._id, IS_SET_EVENT_FRAME)
        lib.is_ExitEvent(self._id, IS_SET_EVENT_FRAME)

    def close(self):
        """
        Close the camera and release associated image memory. Should be called
        when you are done using the camera.
        """
        ret = lib.is_ExitCamera(self._id)
        if ret != IS_SUCCESS:
            print("Failed to close camera")
        else:
            self._in_use = False

    def _bytes_per_line(self):
        num = INT()
        if lib.is_GetImageMemPitch(self._id, pointer(num)) == IS_SUCCESS:
            return num.value
        return None

    def wait_for_frame(self, timeout=0):
        import win32event
        ret = win32event.WaitForSingleObject(self.hEvent, timeout)
        return (ret == win32event.WAIT_OBJECT_0)

    def freeze_frame(self):
        """
        Acquires a single image from the camera and stores it in memory. Can
        be used in conjunction with direct memory access to display an image
        without saving it to file.
        """
        lib.is_FreezeVideo(self._id, self._width, self._height)

    def start_live_video(self, framerate=None):
        self._install_event_handler()
        if framerate is None:
            framerate = IS_GET_FRAMERATE
        newFPS = DOUBLE()
        ret = lib.is_SetFrameRate(self._id, DOUBLE(framerate), pointer(newFPS))
        if ret != IS_SUCCESS:
            print("Error: failed to set framerate")
        else:
            self.framerate = newFPS.value

        lib.is_CaptureVideo(self._id, IS_WAIT)

    def stop_live_video(self):
        lib.is_StopLiveVideo(self._id, IS_WAIT)
        self._uninstall_event_handler()

    def save_frame(self, filename=NULL, filetype=None, live=False):
        """
        Saves the current video image to disk. If no filename is given,
        this will display the 'Save as' dialog. If no filetype is given,
        it will be determined by the extension of the filename, if available.
        If neither exists, the image will be saved as a bitmap.
        """

        # Strip extension from filename, clear extension if it is invalid
        if filename != NULL:
            filename, ext = os.path.splitext(filename)
            if ext.lower() not in ['.bmp', '.jpg', '.png']:
                ext = ''
        else:
            filename, ext = '', ''

        # 'filetype' flag overrides the extension. Default is .bmp
        if filetype:
            ext = '.' + filetype.lower()
        elif not ext:
            ext = '.bmp'

        fdict = {'.bmp':IS_IMG_BMP, '.jpg':IS_IMG_JPG, '.png':IS_IMG_PNG}
        ftype_flag = fdict[ext.lower()]
        filename = filename + ext

        if not live:
            lib.is_FreezeVideo(self._id, self._width, self._height)
        lib.is_SaveImageEx(self._id, filename, ftype_flag, INT(0))

    def _get_max_img_size(self):
        # TODO: Make this more robust
        sInfo = SENSORINFO()
        lib.is_GetSensorInfo(self._id, pointer(sInfo))
        return sInfo.nMaxWidth, sInfo.nMaxHeight
        
    def _value_getter(member_str):
        def getter(self):
            return getattr(self, member_str).value
        return getter

    def _value_setter(member_str):
        def setter(self, value):
            getattr(self, member_str).value = value
        return setter

    def get_image_buffer(self):
        bpl = self.bytes_per_line

        # Create a pointer to the data as a CHAR ARRAY so we can convert it to a buffer
        p_img_mem = self._last_img_mem()
        arr_ptr = cast(p_img_mem, POINTER(c_char * (bpl*self.height)))
        return buffer(arr_ptr.contents) # buffer pointing to array of image data

    def _last_img_mem(self):
        """ Returns a ctypes char-pointer to the starting address of the image memory
        last used for image capturing """
        if self._list_p_img_mem is None:
            # Just using a single image buffer
            return self._p_img_mem
        else:
            # Using a buffer sequence
            nNum = INT()
            pcMem = POINTER(c_char)()
            pcMemLast = POINTER(c_char)()
            lib.is_GetActSeqBuf(self._id, pointer(nNum), pointer(pcMem), pointer(pcMemLast))
            return pcMemLast

    #: Camera ID number
    id = property(lambda self: self._info.dwCameraID) # Read-only

    #: Camera serial number string
    serial = property(lambda self: self._info.SerNo) # Read-only

    #: Camera model number string
    model = property(lambda self: self._info.Model) # Read-only

    #: Number of bytes used by each line of the image
    bytes_per_line = property(lambda self: self._bytes_per_line()) # Read-only

    #: Width of the camera image in pixels
    width = property(_value_getter('_width'), _value_setter('_width'))

    #: Height of the camera image in pixels
    height = property(_value_getter('_height'), _value_setter('_height'))


if __name__ == '__main__':
    cam = get_camera(serial='4002856484')
    cam.open()
    cam.save_frame('cool.jpg')
    cam.close()
