# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz
"""
Module that fakes a local VISA library and PyVISA by talking to a remote server.
"""

from __future__ import unicode_literals, print_function
from codecs import encode, decode
import socket

from messenger import Messenger
from .. import settings

# Create socket immediately upon module import
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host, port = settings['prefs']['default_server'].split(':')
sock.connect((host, int(port)))
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
    s = messenger.recv()
    if len(s) >= 2 and s[:2] == "!!":
        # VISA Error occurred on the server end, recreate it for the client
        err_name, err_message = s[2:].split(':', 1)
        raise error_map[err_name](err_message)
    return s

def _send(command):
    """ Sends a unicode string to the server """
    messenger.send(encode(command, 'utf-8'))

class Instrument(object):
    """ Fakevisa wrapper to PyVISA's Instrument class """
    def __init__(self, id_str):
        self.id_str = id_str

    def ask(self, message):
        """ Sends a string to the server, which sends it to the instrument and
        returns the instrument's response string """
        command = "A{}:{}".format(self.id_str, message)
        _send(command)
        return _receive()
    
    def write(self, message):
        command = "W{}:{}".format(self.id_str, message)
        _send(command)
        _receive() # Dumps 'Success' message and handles any VISA errors
        return

def instrument(name):
    """
    Returns an Instrument instance corresponding to the given resource name
    """
    command = "I{}".format(name)
    _send(command)
    id_str = _receive()
    return Instrument(id_str)

def get_instruments_list():
    """
    Returns a list of resource names of instruments that are connected to the
    server computer
    """
    command = "G"
    _send(command)
    addr_list = _receive().split("%|%")
    return addr_list

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
