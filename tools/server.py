# -*- coding: utf-8 -*-
# Copyright 2014 Nate Bogdanowicz

from __future__ import absolute_import, unicode_literals, print_function
from codecs import encode, decode
import socket
import threading
import visa

from instrumental.visa.messenger import Messenger

# Python 2 and 3 support
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

def _visa_err_response(e):
    response = '!!{}:{}'.format(type(e).__name__, str(e))
    return encode(response, 'utf-8')

# Command syntax [message-bytes]:[command letter]([instrument id]):[message]
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        instruments = []
        messenger = Messenger(self.request)
        while True:
            message = messenger.recv()
            if not message:
                print("Received EOF, quitting...")
                break   # Break on incoming EOF

            if message[0] == b'I':
                name = decode(message[1:], 'utf-8')
                try:
                    instruments.append(visa.instrument(name))
                    response = encode('{}'.format(len(instruments)-1), 'utf-8')
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif message[0] == b'G':
                addr_list = visa.get_instruments_list()
                response = "%|%".join(addr_list)
                response = encode(response, 'utf-8')
            elif message[0] == b'A':
                # Get response from instrument, and send it back to client
                head, body = message.split(':', 1)
                id = int(head[1:])
                try:
                    response = instruments[id].ask(body)
                except visa.Error as e:
                    response = _visa_err_response(e)
            elif message[0] == b'W':
                # Send message to device and return num bytes written
                head, body = message.split(':', 1)
                id = int(head[1:])
                try:
                    instruments[id].write(body)
                    response = 'Success'
                except visa.Error as e:
                    response = _visa_err_respone(e)

            # 'response' should already be encoded
            messenger.send(response)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    HOST, PORT = "171.64.84.122", 28265
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()
