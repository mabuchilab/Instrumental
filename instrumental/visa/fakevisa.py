# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Module that fakes a local VISA library and PyVISA by talking to a remote server.
"""

from __future__ import unicode_literals, print_function
from codecs import encode
import socket

from messenger import Messenger
from .. import conf

# Create socket immediately upon module import
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(1.0)
_connected = False

try:
    host, port = conf.prefs['default_server'].split(':')
except KeyError:
    raise Exception("Error: No default fakevisa server specified in the instrumental.conf")


def _verify_sock_connected():
    global _connected
    if not _connected:
        try:
            sock.connect((host, int(port)))
        except socket.timeout as e:
            raise Exception("Request timed out. Could not find FakeVISA server. " +
                            "Check the server address in instrumental.conf and " +
                            "verify the server program is running.")
        _connected = True

messenger = Messenger(sock)

class VisaIOError(Exception):
    def __init__(self, message):
        super(VisaIOError, self).__init__(message)

class VisaIOWarning(Exception):
    def __init__(self, message):
        super(VisaIOWarning, self).__init__(message)

error_map = {
    'VisaIOError' : VisaIOError,
    'VisaIOWarning' : VisaIOWarning
}

def _receive():
    """ Returns bytes object containing the server's response """
    _verify_sock_connected()
    b = messenger.recv()
    if len(b) >= 2 and b[:2] == b"!!":
        # VISA Error occurred on the server end, recreate it for the client
        err_name, err_message = b[2:].split(b":", 1)
        raise error_map[err_name](err_message)
    return b

def _send(command):
    """ Sends bytes to the server """
    if not isinstance(command, bytes):
        raise TypeError("Command must be bytes object, not unicode string")
    _verify_sock_connected()
    messenger.send(command)

class Instrument(object):
    """ Fakevisa wrapper to PyVISA's Instrument class """
    def __init__(self, id_str):
        self.id_str = id_str
        self.id_byt = encode(id_str, 'utf-8')

    def ask(self, message):
        """ Sends a message to the server, which sends it to the instrument and
        returns the instrument's response string. Note that ask() does not support
        raw bytes. Use a write() with read_raw() for receiving binary data """
        command = b"A:" + self.id_byt + b":" + encode(message, 'utf-8')
        _send(command)
        return _receive()

    def read_raw(self):
        """ Returns message in bytes object """
        command = b"R:" + self.id_byt
        _send(command)
        return _receive()

    def read(self):
        """ Returns message in unicode string """
        resp = self.read_raw()
        return decode(resp, 'utf-8')

    def write_raw(self, message):
        """ Write a bytes message to the device. """
        # Unfortunately, .format() doesn't work for bytes in py3
        command = b"W:" + self.id_byt + b":" + message
        _send(command)
        _receive() # Dumps 'Success' message and handles any VISA errors
    
    def write(self, message):
        """ Write a unicode string message to the device. """
        self.write_raw(encode(message, 'utf-8'))

def instrument(name):
    """
    Returns an Instrument instance corresponding to the given resource name
    """
    command = b'I:' + encode(name, 'utf-8')
    _send(command)
    id_str = _receive()
    return Instrument(id_str)

def get_instruments_list():
    """
    Returns a list of resource names of instruments that are connected to the
    server computer
    """
    command = b'G:'
    _send(command)
    message = encode(_receive(), 'utf-8')
    return message.split("%|%")

if __name__ == '__main__':
    SCOPE_A = "TCPIP::171.64.84.116::INSTR"
    scope = instrument(SCOPE_A)
    print(scope.ask("*IDN?"))
    #print(scope.ask("wfmpre:xincr?"))
    scope.write("data:source ch1")
    scope.write("data:width 2")
    scope.write("data:encdg RIBinary")
    scope.write("data:start 1")
    scope.write("data:stop 10000")
        
    #raw_bin = scope.ask("curve?")

# Clean up at interpreter exit
import atexit
atexit.register(sock.close)
