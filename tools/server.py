# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz

from __future__ import absolute_import, unicode_literals, print_function
from codecs import encode, decode
import threading
import visa
import json

from instrumental.visa.messenger import Messenger

# Python 2 and 3 support
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver


def _visa_err_response(e):
    response = '!!{}:{}'.format(type(e).__name__, str(e))
    return encode(response, 'utf-8')


def log(msg):
    """ Tries to print bytes object 'msg' with ascii encoding, if it
    fails, print out hex representation """
    if isinstance(msg, bytes):
        from binascii import hexlify
        try:
            message = decode(msg, 'ascii')
        except UnicodeDecodeError:
            message = hexlify(msg)
    else:
        message = msg
    print(message)


# Command syntax [message-bytes]:[command letter]:([instrument id]):[message]
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        log("Opening connection...")
        instruments = []
        messenger = Messenger(self.request, is_server=True)
        while True:
            message = messenger.recv()
            if not message:
                log("Received EOF, closing connection.")
                break   # Break on incoming EOF

            cmd, rest = message.split(b':', 1)

            if cmd == b'I':
                kwargs = json.loads(rest)
                name = kwargs.pop('visa_address')
                print(kwargs)
                log("Client asked for instrument '{}'".format(name))
                try:
                    instruments.append(visa.instrument(name, **kwargs))
                    # Reply with the instrument's unique ID number
                    response = encode(str(len(instruments)-1))
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif cmd == b'G':
                log("Client asked for instrument list")
                # addr_list returns a list of unicode strings
                addr_list = visa.get_instruments_list()
                response = "%|%".join(addr_list)
                response = encode(response, 'utf-8')
            elif cmd == b'A':
                # Get response from instrument, and send it back to client
                head, body = rest.split(b':', 1)
                id = int(head)
                log("Client asking '{}' from instrument with id {}...".format(body, id))
                try:
                    # visa.ask() returns a unicode string
                    str_resp = instruments[id].ask(body)
                    response = encode(str_resp, 'utf-8')
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif cmd == b'W':
                # Send message to device and return num bytes written
                head, body = rest.split(b':', 1)
                id = int(head)
                try:
                    log("Client writing '{}' to instrument with id {}...".format(body, id))
                except UnicodeDecodeError:
                    log("Client writing binary data to instrument with id {}...".format(id))
                try:
                    instruments[id].write(body)
                    response = b'Success'
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif cmd == b'R':
                id = int(rest)
                log("Client reading from instrument with id '{}'...".format(id))
                try:
                    # read_raw() returns bytes object
                    response = instruments[id].read_raw()
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif cmd == b'C':
                id = int(rest)
                log("Clien closing instrument with id '{}'...".format(id))
                try:
                    instruments[id].close()
                    response = b'Success'
                except visa.Error as e:
                    response = _visa_err_response(e)

            # 'response' should already be encoded as bytes
            log(b"    responding with '" + response + b"'")
            messenger.send(response)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    HOST, PORT = '', 28265
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    print("Starting fakevisa server...")

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()
